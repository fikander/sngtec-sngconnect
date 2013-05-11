# -*- coding: utf-8 -*-

import datetime
import decimal

import pytz
from sqlalchemy.orm import exc as database_exceptions
from pyramid.view import view_config
from pyramid import httpexceptions
from pyramid.i18n import get_locale_name

from sngconnect.translation import _
from sngconnect.database import (DBSession, DataStreamTemplate, DataStream,
    AlarmDefinition, Message)
from sngconnect.services.message import MessageService
from sngconnect.services.data_stream import DataStreamService
from sngconnect.cassandra import data_streams as data_streams_store
from sngconnect.cassandra import alarms as alarms_store
from sngconnect.telemetry import forms
from sngconnect.telemetry.views.feed.base import FeedViewBase
from sngconnect.telemetry.views.feed.charts import ChartDataMixin

@view_config(
    route_name='sngconnect.telemetry.feed_data_streams',
    request_method='GET',
    renderer='sngconnect.telemetry:templates/feed/data_streams.jinja2',
    permission='sngconnect.telemetry.access'
)
class FeedDataStreams(FeedViewBase):
    def __call__(self):
        data_streams = DBSession.query(DataStream).join(
            DataStreamTemplate
        ).filter(
            DataStream.feed == self.feed,
            DataStreamTemplate.writable == False
        ).order_by(
            DataStreamTemplate.name
        )
        last_data_points = (
            data_streams_store.LastDataPoints().get_last_data_stream_data_points(
                self.feed.id
            )
        )
        data_streams_serialized = []
        for data_stream in data_streams:
            daily_aggregates = (
                data_streams_store.DailyAggregates().get_data_points(
                    data_stream.id,
                    start_date=pytz.utc.localize(datetime.datetime.utcnow()),
                    end_date=pytz.utc.localize(datetime.datetime.utcnow())
                )
            )
            try:
                today = daily_aggregates[0][1]
            except IndexError:
                today = None
            data_point = last_data_points.get(data_stream.id, None)
            if data_point is None:
                last_value = None
            else:
                last_value = {
                    'value': decimal.Decimal(data_point[1]),
                    'date': data_point[0],
                }
            data_streams_serialized.append({
                'id': data_stream.id,
                'name': data_stream.name,
                'measurement_unit': data_stream.measurement_unit,
                'url': self.request.route_url(
                    'sngconnect.telemetry.feed_data_stream',
                    feed_id=self.feed.id,
                    data_stream_label=data_stream.label
                ),
                'last_value': last_value,
                'today': today,
            })
        self.context.update({
            'data_streams': data_streams_serialized,
        })
        return self.context

class FeedDataStreamViewBase(FeedViewBase):

    _data_stream_writable = None

    def __init__(self, request):
        super(FeedDataStreamViewBase, self).__init__(request)
        try:
            query = DBSession.query(DataStream).join(
                DataStreamTemplate
            ).filter(
                DataStream.feed == self.feed,
                (DataStreamTemplate.label ==
                    self.request.matchdict['data_stream_label'])
            )
            if self._data_stream_writable is not None:
                query = query.filter(
                    DataStreamTemplate.writable == self._data_stream_writable
                )
            self.data_stream = query.one()
        except database_exceptions.NoResultFound:
            raise httpexceptions.HTTPBadRequest()

@view_config(
    route_name='sngconnect.telemetry.feed_data_stream',
    renderer='sngconnect.telemetry:templates/feed/data_stream.jinja2',
    permission='sngconnect.telemetry.access'
)
class FeedDataStream(FeedDataStreamViewBase):

    _data_stream_writable = False

    def __call__(self):
        message_service = MessageService(self.request.registry)
        comment_form = forms.CommentForm(csrf_context=self.request)
        minimal_value = DBSession.query(AlarmDefinition).filter(
            AlarmDefinition.data_stream == self.data_stream,
            AlarmDefinition.alarm_type == 'MINIMAL_VALUE'
        ).value('boundary')
        if minimal_value is None:
            minimal_value = self.data_stream.template.default_minimum
        maximal_value = DBSession.query(AlarmDefinition).filter(
            AlarmDefinition.data_stream == self.data_stream,
            AlarmDefinition.alarm_type == 'MAXIMAL_VALUE'
        ).value('boundary')
        if maximal_value is None:
            maximal_value = self.data_stream.template.default_maximum
        value_bounds_form = forms.ValueBoundsForm(
            minimum=minimal_value,
            maximum=maximal_value,
            locale=get_locale_name(self.request),
            csrf_context=self.request
        )
        last_data_point = (
            data_streams_store.LastDataPoints().get_last_data_stream_data_point(
                self.feed.id,
                self.data_stream.id
            )
        )
        if self.request.method == 'POST':
            if 'submit_value_bounds' in self.request.POST:
                value_bounds_form.process(self.request.POST)
                if value_bounds_form.validate():
                    maximum_alarm = None
                    minimum_alarm = None
                    if minimal_value is None:
                        if value_bounds_form.minimum.data is not None:
                            minimum_alarm = AlarmDefinition(
                                data_stream=self.data_stream,
                                alarm_type='MINIMAL_VALUE',
                                boundary=value_bounds_form.minimum.data
                            )
                            DBSession.add(minimum_alarm)
                    else:
                        query = DBSession.query(AlarmDefinition).filter(
                            AlarmDefinition.data_stream == self.data_stream,
                            AlarmDefinition.alarm_type == 'MINIMAL_VALUE',
                        )
                        if value_bounds_form.minimum.data is not None:
                            query.update({
                                'boundary': value_bounds_form.minimum.data
                            })
                            minimum_alarm = query.one()
                        else:
                            query.delete()
                            minimum_alarm = None
                    if maximal_value is None:
                        if value_bounds_form.maximum.data is not None:
                            maximum_alarm = AlarmDefinition(
                                data_stream=self.data_stream,
                                alarm_type='MAXIMAL_VALUE',
                                boundary=value_bounds_form.maximum.data
                            )
                            DBSession.add(maximum_alarm)
                    else:
                        query = DBSession.query(AlarmDefinition).filter(
                            AlarmDefinition.data_stream == self.data_stream,
                            AlarmDefinition.alarm_type == 'MAXIMAL_VALUE',
                        )
                        if value_bounds_form.maximum.data is not None:
                            query.update({
                                'boundary': value_bounds_form.maximum.data
                            })
                            maximum_alarm = query.one()
                        else:
                            query.delete()
                            maximum_alarm = None
                    DBSession.flush()
                    alarms_on = []
                    alarms_off = []
                    if last_data_point is not None:
                        for alarm_definition in [minimum_alarm, maximum_alarm]:
                            if alarm_definition is None:
                                continue
                            if (alarm_definition.check_value(last_data_point[1]) is
                                    None):
                                alarms_off.append(alarm_definition.id)
                            else:
                                alarms_on.append(alarm_definition.id)
                        alarms_store.Alarms().set_alarms_on(
                            self.feed.id,
                            self.data_stream.id,
                            alarms_on,
                            last_data_point[0]
                        )
                        alarms_store.Alarms().set_alarms_off(
                            self.feed.id,
                            self.data_stream.id,
                            alarms_off
                        )
                    self.request.session.flash(
                        _("Parameter allowed values have been successfuly saved."),
                        queue='success'
                    )
                    return httpexceptions.HTTPFound(
                        self.request.route_url(
                            'sngconnect.telemetry.feed_data_stream',
                            feed_id=self.feed.id,
                            data_stream_label=self.data_stream.label
                        )
                    )
                else:
                    self.request.session.flash(
                        _(
                            "There were some problems with your request."
                            " Please check the form for error messages."
                        ),
                        queue='error'
                    )
            elif 'submit_comment' in self.request.POST:
                comment_form.process(self.request.POST)
                if comment_form.validate():
                    message = Message(
                        message_type='COMMENT',
                        date=pytz.utc.localize(datetime.datetime.utcnow()),
                        feed=self.feed,
                        data_stream=self.data_stream,
                        author_id=self.user_id
                    )
                    comment_form.populate_obj(message)
                    message_service.create_message(message)
                    self.request.session.flash(
                        _("Your comment has been successfuly saved."),
                        queue='success'
                    )
                    return httpexceptions.HTTPFound(
                        self.request.route_url(
                            'sngconnect.telemetry.feed_data_stream',
                            feed_id=self.feed.id,
                            data_stream_label=self.data_stream.label
                        )
                    )
                else:
                    self.request.session.flash(
                        _(
                            "There were some problems with your request."
                            " Please check the form for error messages."
                        ),
                        queue='error'
                    )
        hourly_aggregates = data_streams_store.HourlyAggregates().get_data_points(
            self.data_stream.id,
            start_date=pytz.utc.localize(datetime.datetime.utcnow()),
            end_date=pytz.utc.localize(datetime.datetime.utcnow())
        )
        try:
            this_hour = hourly_aggregates[0][1]
            this_hour['mean'] = (
                decimal.Decimal(this_hour['sum'])
                / decimal.Decimal(this_hour['count'])
            )
        except IndexError:
            this_hour = None
        daily_aggregates = data_streams_store.DailyAggregates().get_data_points(
            self.data_stream.id,
            start_date=pytz.utc.localize(datetime.datetime.utcnow()),
            end_date=pytz.utc.localize(datetime.datetime.utcnow())
        )
        try:
            today = daily_aggregates[0][1]
            today['mean'] = (
                decimal.Decimal(today['sum'])
                / decimal.Decimal(today['count'])
            )
        except IndexError:
            today = None
        monthly_aggregates = (
            data_streams_store.MonthlyAggregates().get_data_points(
                self.data_stream.id,
                start_date=pytz.utc.localize(datetime.datetime.utcnow()),
                end_date=pytz.utc.localize(datetime.datetime.utcnow())
            )
        )
        try:
            this_month = monthly_aggregates[0][1]
            this_month['mean'] = (
                decimal.Decimal(this_month['sum'])
                / decimal.Decimal(this_month['count'])
            )
        except IndexError:
            this_month = None
        messages = message_service.get_data_stream_messages(self.data_stream)
        self.context.update({
            'value_bounds_form': value_bounds_form,
            'data_stream': {
                'id': self.data_stream.id,
                'name': self.data_stream.name,
                'measurement_unit': self.data_stream.measurement_unit,
                'description': self.data_stream.description,
                'last_value': {
                    'date': last_data_point[0],
                    'value': decimal.Decimal(last_data_point[1]),
                } if last_data_point else None,
                'this_hour': dict(map(
                    lambda x: (x[0], decimal.Decimal(x[1])),
                    this_hour.items()
                )) if this_hour is not None else None,
                'today': dict(map(
                    lambda x: (x[0], decimal.Decimal(x[1])),
                    today.items()
                )) if today is not None else None,
                'this_month': dict(map(
                    lambda x: (x[0], decimal.Decimal(x[1])),
                    this_month.items()
                )) if this_month is not None else None,
                'url': self.request.route_url(
                    'sngconnect.telemetry.feed_data_stream',
                    feed_id=self.feed.id,
                    data_stream_label=self.data_stream.label
                ),
            },
            'set_range_form': forms.SetChartRangeForm(
                start=datetime.date.today() - datetime.timedelta(days=1),
                end=datetime.date.today(),
                csrf_context=self.request
            ),
            'chart_rendering_data': {
                'type': 'LINEAR',
                'data_url': self.request.route_url(
                    'sngconnect.telemetry.feed_data_stream.chart_data',
                    feed_id=self.feed.id,
                    data_stream_label=self.data_stream.label
                ),
                'data_stream_templates': [
                    {
                        'id': self.data_stream.template.id,
                        'name': self.data_stream.template.name,
                        'measurement_unit': (
                            self.data_stream.template.measurement_unit
                        ),
                        'minimum': self.data_stream.template.default_minimum,
                        'maximum': self.data_stream.template.default_maximum,
                    }
                ],
            },
            'comment_form': comment_form,
            'messages': [
                {
                    'id': message.id,
                    'message_type': message.message_type,
                    'author': (
                        {
                            'id': message.author.id,
                            'name': message.author.name
                        }
                        if message.author is not None
                        else None
                    ),
                    'content': message.content,
                    'date': message.date,
                }
                for message in messages
            ],
        })
        return self.context

@view_config(
    route_name='sngconnect.telemetry.feed_data_stream.chart_data',
    request_method='GET',
    permission='sngconnect.telemetry.access'
)
class FeedDataStreamChartData(ChartDataMixin, FeedDataStreamViewBase):

    def __init__(self, request):
        super(FeedDataStreamChartData, self).__init__(request)
        self.data_stream_templates = [
            self.data_stream.template
        ]
        self.chart_type = 'LINEAR'

@view_config(
    route_name='sngconnect.telemetry.feed_settings',
    request_method='GET',
    renderer='sngconnect.telemetry:templates/feed/settings.jinja2',
    permission='sngconnect.telemetry.access'
)
class FeedSettings(FeedDataStreams):
    def __call__(self):
        if not self.has_settings:
            raise httpexceptions.HTTPNotFound()
        data_streams = DBSession.query(DataStream).join(
            DataStreamTemplate
        ).filter(
            DataStream.feed == self.feed,
            DataStreamTemplate.writable == True
        ).order_by(
            DataStreamTemplate.name
        )
        last_data_points = (
            data_streams_store.LastDataPoints().get_last_data_stream_data_points(
                self.feed.id
            )
        )
        data_streams_serialized = []
        for data_stream in data_streams:
            last_data_point = last_data_points.get(data_stream.id, None)
            data_streams_serialized.append({
                'id': data_stream.id,
                'name': data_stream.name,
                'measurement_unit': data_stream.measurement_unit,
                'url': self.request.route_url(
                    'sngconnect.telemetry.feed_setting',
                    feed_id=self.feed.id,
                    data_stream_label=data_stream.label
                ),
                'requested_value': data_stream.requested_value,
                'value_requested_at': data_stream.value_requested_at,
                'last_value': {
                    'date': last_data_point[0],
                    'value': decimal.Decimal(last_data_point[1]),
                } if last_data_point else None,
            })
        self.context.update({
            'data_streams': data_streams_serialized,
        })
        return self.context

@view_config(
    route_name='sngconnect.telemetry.feed_setting',
    renderer='sngconnect.telemetry:templates/feed/setting.jinja2',
    permission='sngconnect.telemetry.access'
)
class FeedSetting(FeedDataStreamViewBase):

    _data_stream_writable = True

    def __call__(self):
        last_data_point = (
            data_streams_store.LastDataPoints().get_last_data_stream_data_point(
                self.feed.id,
                self.data_stream.id
            )
        )
        value_form = forms.ValueForm(
            value=self.data_stream.requested_value,
            locale=get_locale_name(self.request),
            csrf_context=self.request
        )
        message_service = MessageService(self.request.registry)
        comment_form = forms.CommentForm(csrf_context=self.request)
        if self.request.method == 'POST':
            if 'submit_value' in self.request.POST:
                value_form.process(self.request.POST)
                if value_form.validate():
                    data_stream_service = DataStreamService(
                        self.request.registry
                    )
                    data_stream_service.set_requested_value(
                        self.data_stream,
                        value_form.value.data
                    )
                    self.request.session.flash(
                        _("Setting value has been successfuly saved."),
                        queue='success'
                    )
                    return httpexceptions.HTTPFound(
                        self.request.route_url(
                            'sngconnect.telemetry.feed_setting',
                            feed_id=self.feed.id,
                            data_stream_label=self.data_stream.label
                        )
                    )
                else:
                    self.request.session.flash(
                        _(
                            "There were some problems with your request."
                            " Please check the form for error messages."
                        ),
                        queue='error'
                    )
            elif 'submit_comment' in self.request.POST:
                comment_form.process(self.request.POST)
                if comment_form.validate():
                    message = Message(
                        message_type='COMMENT',
                        date=pytz.utc.localize(datetime.datetime.utcnow()),
                        feed=self.feed,
                        data_stream=self.data_stream,
                        author_id=self.user_id
                    )
                    comment_form.populate_obj(message)
                    message_service.create_message(message)
                    self.request.session.flash(
                        _("Your comment has been successfuly saved."),
                        queue='success'
                    )
                    return httpexceptions.HTTPFound(
                        self.request.route_url(
                            'sngconnect.telemetry.feed_setting',
                            feed_id=self.feed.id,
                            data_stream_label=self.data_stream.label
                        )
                    )
                else:
                    self.request.session.flash(
                        _(
                            "There were some problems with your request."
                            " Please check the form for error messages."
                        ),
                        queue='error'
                    )
        messages = message_service.get_data_stream_messages(self.data_stream)
        self.context.update({
            'value_form': value_form,
            'data_stream': {
                'id': self.data_stream.id,
                'name': self.data_stream.name,
                'measurement_unit': self.data_stream.measurement_unit,
                'description': self.data_stream.description,
                'requested_value': self.data_stream.requested_value,
                'value_requested_at': self.data_stream.value_requested_at,
                'last_value': {
                    'date': last_data_point[0],
                    'value': decimal.Decimal(last_data_point[1]),
                } if last_data_point else None,
                'url': self.request.route_url(
                    'sngconnect.telemetry.feed_setting',
                    feed_id=self.feed.id,
                    data_stream_label=self.data_stream.label
                ),
            },
            'set_range_form': forms.SetChartRangeForm(
                start=datetime.date.today() - datetime.timedelta(days=1),
                end=datetime.date.today(),
                csrf_context=self.request
            ),
            'chart_rendering_data': {
                'type': 'LINEAR',
                'data_url': self.request.route_url(
                    'sngconnect.telemetry.feed_data_stream.chart_data',
                    feed_id=self.feed.id,
                    data_stream_label=self.data_stream.label
                ),
                'data_stream_templates': [
                    {
                        'id': self.data_stream.template.id,
                        'name': self.data_stream.template.name,
                        'measurement_unit': (
                            self.data_stream.template.measurement_unit
                        ),
                        'minimum': self.data_stream.template.default_minimum,
                        'maximum': self.data_stream.template.default_maximum,
                    }
                ],
            },
            'comment_form': comment_form,
            'messages': [
                {
                    'id': message.id,
                    'message_type': message.message_type,
                    'author': (
                        {
                            'id': message.author.id,
                            'name': message.author.name
                        }
                        if message.author is not None
                        else None
                    ),
                    'content': message.content,
                    'date': message.date,
                }
                for message in messages
            ],
        })
        return self.context
