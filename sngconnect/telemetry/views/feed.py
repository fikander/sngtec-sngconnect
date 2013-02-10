# -*- coding: utf-8 -*-

import datetime
import decimal
import json

import isodate
import pytz
import sqlalchemy as sql
from sqlalchemy.orm import exc as database_exceptions, joinedload
from pyramid.response import Response
from pyramid.view import view_config
from pyramid import httpexceptions
from pyramid.i18n import get_locale_name
from pyramid.security import authenticated_userid, has_permission

from sngconnect.translation import _
from sngconnect.database import (DBSession, Feed, DataStreamTemplate,
    DataStream, AlarmDefinition, FeedUser, User, ChartDefinition, FeedTemplate,
    Message)
from sngconnect.services.message import MessageService
from sngconnect.services.user import UserService
from sngconnect.cassandra import data_streams as data_streams_store
from sngconnect.cassandra import alarms as alarms_store
from sngconnect.telemetry import forms, schemas

@view_config(
    route_name='sngconnect.telemetry.feeds',
    request_method='GET',
    permission='sngconnect.telemetry.access'
)
def feeds(request):
    return httpexceptions.HTTPSeeOther(
        request.route_url('sngconnect.telemetry.dashboard')
    )

@view_config(
    route_name='sngconnect.telemetry.feeds.new',
    renderer='sngconnect.telemetry:templates/feed/new.jinja2',
    permission='sngconnect.telemetry.create_feed'
)
def feeds_new(request):
    try:
        user = DBSession.query(User).filter(
            User.id == authenticated_userid(request)
        ).one()
    except database_exceptions.NoResultFound:
        raise httpexceptions.HTTPForbidden()
    feed_templates = DBSession.query(FeedTemplate).order_by(
        sql.asc(FeedTemplate.name)
    )
    if user.role_maintainer == True:
        forced_user = None
    else:
        forced_user = user
    create_form = forms.CreateFeedForm(
        feed_templates,
        forced_user,
        locale=get_locale_name(request),
        csrf_context=request
    )
    if request.method == 'POST':
        create_form.process(request.POST)
        if create_form.validate():
            feed = Feed()
            create_form.populate_obj(feed)
            feed.created = pytz.utc.localize(datetime.datetime.utcnow())
            feed.regenerate_api_key()
            feed.regenerate_activation_code()
            DBSession.add(feed)
            feed_user = FeedUser(
                feed=feed,
                role_user=True,
                can_change_permissions=True
            )
            if forced_user is None:
                feed_user.user = create_form.get_owner()
                feed_maintainer = FeedUser(
                    feed=feed,
                    user=user,
                    role_maintainer=True,
                    can_change_permissions=True
                )
                DBSession.add(feed_maintainer)
            else:
                feed_user.user = user
            DBSession.add(feed_user)
            request.session.flash(
                _(
                    "New device has been added. Go to the device dashboard to"
                    " obtain the activation code."
                ),
                queue='success'
            )
            return httpexceptions.HTTPFound(
                request.route_url('sngconnect.telemetry.dashboard')
            )
        else:
            request.session.flash(
                _(
                    "There were some problems with your request."
                    " Please check the form for error messages."
                ),
                queue='error'
            )
    return {
        'create_form': create_form,
    }

class FeedViewBase(object):

    def __init__(self, request):
        self.user_id = authenticated_userid(request)
        can_access_all = has_permission(
            'sngconnect.telemetry.access_all',
            request.context,
            request
        )
        can_change_all = has_permission(
            'sngconnect.telemetry.change_all',
            request.context,
            request
        )
        try:
            feed = DBSession.query(Feed).filter(
                Feed.id == request.matchdict['feed_id']
            ).one()
        except database_exceptions.NoResultFound:
            raise httpexceptions.HTTPNotFound()
        try:
            feed_user = DBSession.query(FeedUser).filter(
                FeedUser.feed_id == feed.id,
                FeedUser.user_id == self.user_id
            ).one()
        except database_exceptions.NoResultFound:
            feed_user = None
            if not can_access_all:
                raise httpexceptions.HTTPForbidden()
            feed_permissions = {
                'can_change_permissions': can_change_all,
            }
        else:
            feed_permissions = {
                'can_change_permissions': feed_user.can_change_permissions,
            }
        self.request = request
        self.feed = feed
        try:
            self.user = DBSession.query(User).filter(
                User.id == self.user_id
            ).one()
        except database_exceptions.NoResultFound:
            raise httpexceptions.HTTPForbidden()
        self.feed_user = feed_user
        self.feed_permissions = feed_permissions
        settings_count = DBSession.query(DataStream).join(
            DataStreamTemplate
        ).filter(
            DataStream.feed == self.feed,
            DataStreamTemplate.writable == True
        ).count()
        self.has_settings = (settings_count > 0)
        self.active_alarms = alarms_store.Alarms().get_active_alarms(feed.id)
        self.active_alarms_count = sum(
            map(len, self.active_alarms.itervalues())
        )
        self.context = {
            'active_alarms_count': self.active_alarms_count,
            'feed': {
                'id': feed.id,
                'name': feed.name,
                'description': feed.description,
                'address': feed.address,
                'latitude': feed.latitude,
                'longitude': feed.longitude,
                'created': feed.created,
                'has_settings': self.has_settings,
                'image_url': feed.template.get_image_url(request),
                'dashboard_url': request.route_url(
                    'sngconnect.telemetry.feed_dashboard',
                    feed_id=feed.id
                ),
                'charts_url': request.route_url(
                    'sngconnect.telemetry.feed_charts',
                    feed_id=feed.id
                ),
                'data_streams_url': request.route_url(
                    'sngconnect.telemetry.feed_data_streams',
                    feed_id=feed.id
                ),
                'settings_url': request.route_url(
                    'sngconnect.telemetry.feed_settings',
                    feed_id=feed.id
                ),
                'permissions_url': request.route_url(
                    'sngconnect.telemetry.feed_permissions',
                    feed_id=feed.id
                ),
                'history_url': request.route_url(
                    'sngconnect.telemetry.feed_history',
                    feed_id=feed.id
                ),
            },
            'feed_permissions': feed_permissions,
        }

    def __call__(self):
        return self.context

@view_config(
    route_name='sngconnect.telemetry.feed_dashboard',
    request_method='GET',
    renderer='sngconnect.telemetry:templates/feed/dashboard.jinja2',
    permission='sngconnect.telemetry.access'
)
class FeedDashboard(FeedViewBase):
    def __call__(self):
        # Activation
        if self.feed.activation_code is not None:
            if self.feed.has_activation_code_expired():
                self.feed.regenerate_activation_code()
                DBSession.add(self.feed)
            activation = {
                'code': ':'.join((
                    str(self.feed.id),
                    self.feed.activation_code,
                )),
            }
        else:
            activation = None
        # Last updated
        last_updated = (
            data_streams_store.LastDataPoints().get_last_data_stream_datetime(
                self.feed.id
            )
        )
        # Messages
        message_service = MessageService(self.request)
        unconfirmed_messages = message_service.get_unconfirmed_messages(
            self.user,
            feed=self.feed
        )
        # Alarms
        active_alarms = {}
        for data_stream_id, data in self.active_alarms.iteritems():
            active_alarms.update(data)
        alarm_definitions = DBSession.query(AlarmDefinition).options(
            joinedload(AlarmDefinition.data_stream)
        ).filter(
            AlarmDefinition.id.in_(active_alarms.keys())
        )
        # Data streams
        data_streams = DBSession.query(DataStream).join(
            DataStreamTemplate
        ).filter(
            DataStream.feed == self.feed,
            DataStreamTemplate.show_on_dashboard == True
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
            data_point = last_data_points.get(data_stream.id, None)
            if data_point is None:
                last_value = None
            else:
                last_value = {
                    'value': decimal.Decimal(data_point[1]),
                    'date': data_point[0],
                }
            data_stream_serialized = {
                'id': data_stream.id,
                'name': data_stream.name,
                'measurement_unit': data_stream.measurement_unit,
                'url': self.request.route_url(
                    (
                        'sngconnect.telemetry.feed_setting'
                        if data_stream.writable
                        else 'sngconnect.telemetry.feed_data_stream'
                    ),
                    feed_id=self.feed.id,
                    data_stream_label=data_stream.label
                ),
                'last_value': last_value,
                'writable': data_stream.writable,
            }
            if data_stream.writable:
                data_stream_serialized.update({
                    'value_url': self.request.route_url(
                        'sngconnect.telemetry.feed_dashboard.set_value',
                        feed_id=self.feed.id,
                        data_stream_template_id=data_stream.template.id
                    ),
                    'value_form': forms.ValueForm(
                        value=data_stream.requested_value,
                        locale=get_locale_name(self.request),
                        csrf_context=self.request
                    ),
                    'requested_value': data_stream.requested_value,
                })
            else:
                daily_aggregates = (
                    data_streams_store.DailyAggregates().get_data_points(
                        data_stream.id,
                        start_date=pytz.utc.localize(datetime.datetime.utcnow()),
                        end_date=pytz.utc.localize(datetime.datetime.utcnow())
                    )
                )
                try:
                    data_stream_serialized['today'] = daily_aggregates[0][1]
                except IndexError:
                    data_stream_serialized['today'] = None
            data_streams_serialized.append(data_stream_serialized)
        parameters = filter(
            lambda data_stream: not data_stream['writable'],
            data_streams_serialized
        )
        settings = filter(
            lambda data_stream: data_stream['writable'],
            data_streams_serialized
        )
        # Charts
        chart_definitions = DBSession.query(ChartDefinition).filter(
            ChartDefinition.feed_template == self.feed.template,
            ChartDefinition.feed == None,
            ChartDefinition.show_on_dashboard == True
        ).order_by(
            ChartDefinition.name
        ).all()
        charts = [
            {
                'definition': {
                    'id': chart_definition.id,
                    'name': chart_definition.name,
                },
                'rendering_data': {
                    'id': chart_definition.id,
                    'name': chart_definition.name,
                    'type': chart_definition.chart_type,
                    'data_url': self.request.route_url(
                        'sngconnect.telemetry.feed_chart.data',
                        feed_id=self.feed.id,
                        chart_definition_id=chart_definition.id
                    ),
                    'data_stream_templates': [
                        {
                            'id': template.id,
                            'name': template.name,
                            'measurement_unit': template.measurement_unit,
                        }
                        for template in sorted(
                            chart_definition.data_stream_templates,
                            None,
                            lambda template: template.id
                        )
                    ],
                },
            }
            for chart_definition in chart_definitions
        ]
        self.context.update({
            'last_updated': last_updated,
            'parameters': parameters,
            'settings': settings,
            'charts': charts,
            'activation': activation,
            'active_alarms': [
                {
                    'id': alarm_definition.id,
                    'alarm_type': alarm_definition.alarm_type,
                    'boundary': alarm_definition.boundary,
                    'data_stream': (
                        {
                            'id': alarm_definition.data_stream.id,
                            'name': alarm_definition.data_stream.name,
                            'url': self.request.route_url(
                                'sngconnect.telemetry.feed_data_stream',
                                feed_id=self.feed.id,
                                data_stream_label=(
                                    alarm_definition.data_stream.label
                                )
                            ),
                        }
                        if alarm_definition.data_stream is not None else None
                    ),
                    'activation_date': active_alarms[alarm_definition.id],
                }
                for alarm_definition in alarm_definitions
            ],
            'important_messages': [
                {
                    'id': message.id,
                    'message_type': message.message_type,
                    'content': message.content,
                    'date': message.date,
                    'confirm_url': self.request.route_url(
                        'sngconnect.telemetry.confirm_message'
                    ),
                    'confirm_form': forms.ConfirmMessageForm(
                        id=message.id,
                        csrf_context=self.request
                    ),
                }
                for message in unconfirmed_messages
            ],
        })
        return self.context

@view_config(
    route_name='sngconnect.telemetry.feed_dashboard.set_value',
    request_method='POST',
    renderer='sngconnect.telemetry:templates/feed/setting.jinja2',
    permission='sngconnect.telemetry.access'
)
class FeedDashboardSetValue(FeedViewBase):
    def __call__(self):
        if not self.request.is_xhr:
            raise httpexceptions.HTTPBadRequest()
        try:
            data_stream = DBSession.query(DataStream).join(
                DataStreamTemplate
            ).filter(
                DataStream.feed == self.feed,
                DataStreamTemplate.writable == True,
                DataStreamTemplate.id ==
                    self.request.matchdict['data_stream_template_id']
            ).one()
        except database_exceptions.NoResultFound:
            raise httpexceptions.HTTPNotFound()
        value_form = forms.ValueForm(
            value=data_stream.requested_value,
            locale=get_locale_name(self.request),
            csrf_context=self.request
        )
        if self.request.method == 'POST':
            value_form.process(self.request.POST)
            if value_form.validate():
                DBSession.query(DataStream).filter(
                    DataStream.id == data_stream.id
                ).update({
                    'requested_value': value_form.value.data,
                    'value_requested_at': pytz.utc.localize(
                        datetime.datetime.utcnow()
                    ),
                })
                return Response(
                    json.dumps({'success': True}),
                    content_type='application/json'
                )
        return Response(
            json.dumps({'success': False}),
            content_type='application/json'
        )

@view_config(
    route_name='sngconnect.telemetry.feed_charts',
    request_method='GET',
    renderer='sngconnect.telemetry:templates/feed/charts.jinja2',
    permission='sngconnect.telemetry.access'
)
class FeedCharts(FeedViewBase):
    def __init__(self, request):
        super(FeedCharts, self).__init__(request)
        self.chart_definitions = DBSession.query(ChartDefinition).join(
            FeedTemplate,
            Feed
        ).filter(
            sql.or_(
                FeedTemplate.id == self.feed.template_id,
                Feed.id == self.feed.id
            )
        ).order_by(
            ChartDefinition.feed_id,
            ChartDefinition.name
        ).all()
        self.context.update({
            'chart_definitions': [
                {
                    'id': chart_definition.id,
                    'name': chart_definition.name,
                    'description': chart_definition.description,
                    'editable': chart_definition.feed is not None,
                    'change_url': request.route_url(
                        'sngconnect.telemetry.feed_chart.update',
                        feed_id=self.feed.id,
                        chart_definition_id=chart_definition.id
                    ),
                    'change_form': forms.UpdateChartDefinitionForm(
                        chart_definition.id,
                        self.feed,
                        self.feed.template.data_stream_templates,
                        obj=chart_definition,
                        csrf_context=self.request
                    ),
                    'delete_url': request.route_url(
                        'sngconnect.telemetry.feed_chart.delete',
                        feed_id=self.feed.id,
                        chart_definition_id=chart_definition.id
                    ),
                    'delete_form': forms.DeleteChartDefinitionForm(
                        csrf_context=self.request
                    ),
                    'url': self.request.route_url(
                        'sngconnect.telemetry.feed_chart',
                        feed_id=self.feed.id,
                        chart_definition_id=chart_definition.id
                    ),
                }
                for chart_definition in self.chart_definitions
            ],
            'create_chart_url': self.request.route_url(
                'sngconnect.telemetry.feed_charts.create',
                feed_id=self.feed.id
            ),
            'create_chart_form': {
                'LINEAR': forms.CreateChartDefinitionForm(
                    self.feed,
                    self.feed.template.data_stream_templates,
                    chart_type='LINEAR',
                    csrf_context=self.request
                ),
                'DIFFERENTIAL': forms.CreateChartDefinitionForm(
                    self.feed,
                    self.feed.template.data_stream_templates,
                    chart_type='DIFFERENTIAL',
                    csrf_context=self.request
                ),
            },
            'chart': None,
        })

@view_config(
    route_name='sngconnect.telemetry.feed_charts.create',
    request_method='POST',
    permission='sngconnect.telemetry.access'
)
class FeedChartsCreate(FeedViewBase):
    def __call__(self):
        create_chart_form = forms.CreateChartDefinitionForm(
            self.feed,
            self.feed.template.data_stream_templates,
            csrf_context=self.request
        )
        create_chart_form.process(self.request.POST)
        data_stream_templates_dict = dict((
            (template.id, template)
            for template in self.feed.template.data_stream_templates
        ))
        if create_chart_form.validate():
            chart_definition = ChartDefinition(
                feed_template=self.feed.template,
                feed=self.feed
            )
            create_chart_form.populate_obj(chart_definition)
            for id in create_chart_form.data_stream_template_ids.data:
                chart_definition.data_stream_templates.append(
                    data_stream_templates_dict[id]
                )
            DBSession.add(chart_definition)
            return Response(
                json.dumps({
                    'redirect': None,
                }),
                content_type='application/json'
            )
        return Response(
            json.dumps({
                'errors': create_chart_form.errors,
            }),
            content_type='application/json'
        )

@view_config(
    route_name='sngconnect.telemetry.feed_chart',
    request_method='GET',
    renderer='sngconnect.telemetry:templates/feed/chart.jinja2',
    permission='sngconnect.telemetry.access'
)
class FeedChart(FeedCharts):
    def __call__(self):
        try:
            chart_definition = filter(
                lambda cd: (
                    cd.id == int(self.request.matchdict['chart_definition_id'])
                ),
                self.chart_definitions
            )[0]
        except (ValueError, IndexError):
            raise httpexceptions.HTTPNotFound()
        self.context['chart'] = {
            'definition': {
                'id': chart_definition.id,
                'name': chart_definition.name,
            },
            'rendering_data': {
                'id': chart_definition.id,
                'name': chart_definition.name,
                'type': chart_definition.chart_type,
                'data_url': self.request.route_url(
                    'sngconnect.telemetry.feed_chart.data',
                    feed_id=self.feed.id,
                    chart_definition_id=chart_definition.id
                ),
                'data_stream_templates': [
                    {
                        'id': template.id,
                        'name': template.name,
                        'measurement_unit': template.measurement_unit,
                    }
                    for template in sorted(
                        chart_definition.data_stream_templates,
                        None,
                        lambda template: template.id
                    )
                ],
            },
        }
        self.context['set_range_form'] = forms.SetChartRangeForm(
            start=datetime.date.today() - datetime.timedelta(days=1),
            end=datetime.date.today(),
            csrf_context=self.request
        )
        return self.context

class FeedChartApiViewBase(FeedViewBase):
    def __init__(self, request):
        super(FeedChartApiViewBase, self).__init__(request)
        try:
            self.chart_definition = DBSession.query(ChartDefinition).filter(
                (ChartDefinition.id ==
                    self.request.matchdict['chart_definition_id']),
                ChartDefinition.feed_template_id == self.feed.template_id
            ).one()
        except database_exceptions.NoResultFound:
            raise httpexceptions.HTTPNotFound()

@view_config(
    route_name='sngconnect.telemetry.feed_chart.data',
    request_method='GET',
    permission='sngconnect.telemetry.access'
)
class FeedChartData(FeedChartApiViewBase):
    def __call__(self):
        try:
            last = max(0, int(self.request.GET['last']))
        except (KeyError, ValueError):
            last = None
        try:
            end = isodate.parse_datetime(self.request.GET['end'])
        except (KeyError, isodate.ISO8601Error):
            end = None
        try:
            start = isodate.parse_datetime(self.request.GET['start'])
        except (KeyError, isodate.ISO8601Error):
            start = None
        if end is None:
            end = pytz.utc.localize(datetime.datetime.utcnow())
        if start is None:
            if last is None:
                start = end - datetime.timedelta(hours=24)
            else:
                start = end - datetime.timedelta(hours=last)
        data_stream_template_ids = map(
            lambda dst: dst.id,
            self.chart_definition.data_stream_templates
        )
        data_stream_ids = DBSession.query(DataStream.id).filter(
            DataStream.feed == self.feed,
            DataStream.template_id.in_(data_stream_template_ids)
        ).order_by(
            DataStream.template_id
        )
        series_appstruct = []
        if start is not None and last is not None:
            delta = datetime.timedelta(hours=last)
        else:
            delta = end - start
        aggregate = True
        if (self.chart_definition.chart_type != 'DIFFERENTIAL' and
                delta <= datetime.timedelta(hours=24)):
            data_store = data_streams_store.Measurements()
            aggregate = False
        elif delta <= datetime.timedelta(days=35):
            data_store = data_streams_store.HourlyAggregates()
        else:
            data_store = data_streams_store.DailyAggregates()
        for data_stream_id in map(lambda x: x.id, data_stream_ids):
            data_points = data_store.get_data_points(
                data_stream_id,
                start_date=start,
                end_date=end
            )
            if aggregate:
                if self.chart_definition.chart_type == 'DIFFERENTIAL':
                    data_points = map(
                        lambda dp: (
                            dp[0],
                            decimal.Decimal(dp[1]['minimum'])
                        ),
                        data_points
                    )
                else:
                    data_points = map(
                        lambda dp: (
                            dp[0],
                            (
                                decimal.Decimal(dp[1]['sum']) /
                                    decimal.Decimal(dp[1]['count'])
                            ).quantize(decimal.Decimal('.01'))
                        ),
                        data_points
                    )
            else:
                data_points = map(
                    lambda dp: (
                        dp[0],
                        decimal.Decimal(dp[1])
                    ),
                    data_points
                )
            if self.chart_definition.chart_type == 'DIFFERENTIAL':
                differential_data_points = []
                for i in range(len(data_points)):
                    try:
                        differential_data_points.append((
                            data_points[i][0],
                            data_points[i + 1][1] - data_points[i][1]
                        ))
                    except IndexError:
                        break
                data_points = differential_data_points
            series_appstruct.append(
                data_points
            )
        return Response(
            json.dumps(schemas.ChartDataResponse().serialize(series_appstruct)),
            content_type='application/json'
        )

@view_config(
    route_name='sngconnect.telemetry.feed_chart.update',
    request_method='POST',
    permission='sngconnect.telemetry.access'
)
class FeedChartsUpdate(FeedChartApiViewBase):
    def __call__(self):
        update_chart_form = forms.UpdateChartDefinitionForm(
            self.chart_definition.id,
            self.feed,
            self.feed.template.data_stream_templates,
            csrf_context=self.request
        )
        update_chart_form.process(self.request.POST)
        data_stream_templates_dict = dict((
            (template.id, template)
            for template in self.feed.template.data_stream_templates
        ))
        if update_chart_form.validate():
            update_chart_form.populate_obj(self.chart_definition)
            self.chart_definition.data_stream_templates = []
            for id in update_chart_form.data_stream_template_ids.data:
                self.chart_definition.data_stream_templates.append(
                    data_stream_templates_dict[id]
                )
            DBSession.add(self.chart_definition)
            return Response(
                json.dumps({
                    'redirect': None,
                }),
                content_type='application/json'
            )
        return Response(
            json.dumps({
                'errors': update_chart_form.errors,
            }),
            content_type='application/json'
        )

@view_config(
    route_name='sngconnect.telemetry.feed_chart.delete',
    request_method='POST',
    permission='sngconnect.telemetry.access'
)
class FeedChartsDelete(FeedChartApiViewBase):
    def __call__(self):
        delete_chart_form = forms.DeleteChartDefinitionForm(
            csrf_context=self.request
        )
        delete_chart_form.process(self.request.POST)
        if delete_chart_form.validate():
            DBSession.delete(self.chart_definition)
            return Response(
                json.dumps({
                    'redirect': self.request.route_url(
                        'sngconnect.telemetry.feed_charts',
                        feed_id=self.feed.id
                    ),
                }),
                content_type='application/json'
            )
        return Response(status_code=400)

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

@view_config(
    route_name='sngconnect.telemetry.feed_data_stream',
    renderer='sngconnect.telemetry:templates/feed/data_stream.jinja2',
    permission='sngconnect.telemetry.access'
)
class FeedDataStream(FeedViewBase):
    def __call__(self):
        try:
            data_stream = DBSession.query(DataStream).join(
                DataStreamTemplate
            ).filter(
                DataStream.feed == self.feed,
                DataStreamTemplate.writable == False,
                (DataStreamTemplate.label ==
                    self.request.matchdict['data_stream_label'])
            ).one()
        except database_exceptions.NoResultFound:
            raise httpexceptions.HTTPNotFound()
        message_service = MessageService(self.request)
        comment_form = forms.CommentForm(csrf_context=self.request)
        minimal_value = DBSession.query(AlarmDefinition).filter(
            AlarmDefinition.data_stream == data_stream,
            AlarmDefinition.alarm_type == 'MINIMAL_VALUE'
        ).value('boundary')
        maximal_value = DBSession.query(AlarmDefinition).filter(
            AlarmDefinition.data_stream == data_stream,
            AlarmDefinition.alarm_type == 'MAXIMAL_VALUE'
        ).value('boundary')
        value_bounds_form = forms.ValueBoundsForm(
            minimum=minimal_value,
            maximum=maximal_value,
            locale=get_locale_name(self.request),
            csrf_context=self.request
        )
        last_data_point = (
            data_streams_store.LastDataPoints().get_last_data_stream_data_point(
                self.feed.id,
                data_stream.id
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
                                data_stream=data_stream,
                                alarm_type='MINIMAL_VALUE',
                                boundary=value_bounds_form.minimum.data
                            )
                            DBSession.add(minimum_alarm)
                    else:
                        query = DBSession.query(AlarmDefinition).filter(
                            AlarmDefinition.data_stream == data_stream,
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
                                data_stream=data_stream,
                                alarm_type='MAXIMAL_VALUE',
                                boundary=value_bounds_form.maximum.data
                            )
                            DBSession.add(maximum_alarm)
                    else:
                        query = DBSession.query(AlarmDefinition).filter(
                            AlarmDefinition.data_stream == data_stream,
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
                            data_stream.id,
                            alarms_on,
                            last_data_point[0]
                        )
                        alarms_store.Alarms().set_alarms_off(
                            self.feed.id,
                            data_stream.id,
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
                            data_stream_label=data_stream.label
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
                        data_stream=data_stream,
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
                            data_stream_label=data_stream.label
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
            data_stream.id,
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
            data_stream.id,
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
                data_stream.id,
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
        last_day_values = data_streams_store.Measurements().get_data_points(
            data_stream.id,
            start_date=pytz.utc.localize(
                datetime.datetime.utcnow() - datetime.timedelta(days=1)
            ),
            end_date=pytz.utc.localize(datetime.datetime.utcnow())
        )
        last_week_values = data_streams_store.HourlyAggregates().get_data_points(
            data_stream.id,
            start_date=pytz.utc.localize(
                datetime.datetime.utcnow() - datetime.timedelta(days=7)
            ),
            end_date=pytz.utc.localize(datetime.datetime.utcnow())
        )
        for i in range(len(last_week_values)):
            last_week_values[i][1]['mean'] = (
                decimal.Decimal(last_week_values[i][1]['sum'])
                / decimal.Decimal(last_week_values[i][1]['count'])
            )
        last_year_values = data_streams_store.DailyAggregates().get_data_points(
            data_stream.id,
            start_date=pytz.utc.localize(
                datetime.datetime.utcnow() - datetime.timedelta(days=365)
            ),
            end_date=pytz.utc.localize(datetime.datetime.utcnow())
        )
        for i in range(len(last_year_values)):
            last_year_values[i][1]['mean'] = (
                decimal.Decimal(last_year_values[i][1]['sum'])
                / decimal.Decimal(last_year_values[i][1]['count'])
            )
        messages = message_service.get_data_stream_messages(data_stream)
        self.context.update({
            'value_bounds_form': value_bounds_form,
            'data_stream': {
                'id': data_stream.id,
                'name': data_stream.name,
                'measurement_unit': data_stream.measurement_unit,
                'description': data_stream.description,
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
                'last_day_values': last_day_values,
                'last_week_values': last_week_values,
                'last_year_values': last_year_values,
                'url': self.request.route_url(
                    'sngconnect.telemetry.feed_data_stream',
                    feed_id=self.feed.id,
                    data_stream_label=data_stream.label
                ),
            },
            'comment_form': comment_form,
            'messages': [
                {
                    'id': message.id,
                    'message_type': message.message_type,
                    'author': (
                        {
                            'id': message.author.id,
                            'name': message.author.email
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
class FeedSetting(FeedViewBase):
    def __call__(self):
        try:
            data_stream = DBSession.query(DataStream).join(
                DataStreamTemplate
            ).filter(
                DataStream.feed == self.feed,
                DataStreamTemplate.writable == True,
                (DataStreamTemplate.label ==
                    self.request.matchdict['data_stream_label'])
            ).one()
        except database_exceptions.NoResultFound:
            raise httpexceptions.HTTPNotFound()
        last_data_point = (
            data_streams_store.LastDataPoints().get_last_data_stream_data_point(
                self.feed.id,
                data_stream.id
            )
        )
        value_form = forms.ValueForm(
            value=data_stream.requested_value,
            locale=get_locale_name(self.request),
            csrf_context=self.request
        )
        message_service = MessageService(self.request)
        comment_form = forms.CommentForm(csrf_context=self.request)
        if self.request.method == 'POST':
            if 'submit_value' in self.request.POST:
                value_form.process(self.request.POST)
                if value_form.validate():
                    DBSession.query(DataStream).filter(
                        DataStream.id == data_stream.id
                    ).update({
                        'requested_value': value_form.value.data,
                        'value_requested_at': pytz.utc.localize(
                            datetime.datetime.utcnow()
                        ),
                    })
                    self.request.session.flash(
                        _("Setting value has been successfuly saved."),
                        queue='success'
                    )
                    return httpexceptions.HTTPFound(
                        self.request.route_url(
                            'sngconnect.telemetry.feed_setting',
                            feed_id=self.feed.id,
                            data_stream_label=data_stream.label
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
                        data_stream=data_stream,
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
                            data_stream_label=data_stream.label
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
        last_day_values = data_streams_store.Measurements().get_data_points(
            data_stream.id,
            start_date=pytz.utc.localize(
                datetime.datetime.utcnow() - datetime.timedelta(days=1)
            ),
            end_date=pytz.utc.localize(datetime.datetime.utcnow())
        )
        last_week_values = data_streams_store.HourlyAggregates().get_data_points(
            data_stream.id,
            start_date=pytz.utc.localize(
                datetime.datetime.utcnow() - datetime.timedelta(days=7)
            ),
            end_date=pytz.utc.localize(datetime.datetime.utcnow())
        )
        for i in range(len(last_week_values)):
            last_week_values[i][1]['mean'] = (
                decimal.Decimal(last_week_values[i][1]['sum'])
                / decimal.Decimal(last_week_values[i][1]['count'])
            )
        last_year_values = data_streams_store.DailyAggregates().get_data_points(
            data_stream.id,
            start_date=pytz.utc.localize(
                datetime.datetime.utcnow() - datetime.timedelta(days=365)
            ),
            end_date=pytz.utc.localize(datetime.datetime.utcnow())
        )
        for i in range(len(last_year_values)):
            last_year_values[i][1]['mean'] = (
                decimal.Decimal(last_year_values[i][1]['sum'])
                / decimal.Decimal(last_year_values[i][1]['count'])
            )
        messages = message_service.get_data_stream_messages(data_stream)
        self.context.update({
            'value_form': value_form,
            'data_stream': {
                'id': data_stream.id,
                'name': data_stream.name,
                'measurement_unit': data_stream.measurement_unit,
                'description': data_stream.description,
                'requested_value': data_stream.requested_value,
                'value_requested_at': data_stream.value_requested_at,
                'last_value': {
                    'date': last_data_point[0],
                    'value': decimal.Decimal(last_data_point[1]),
                } if last_data_point else None,
                'last_day_values': last_day_values,
                'last_week_values': last_week_values,
                'last_year_values': last_year_values,
                'url': self.request.route_url(
                    'sngconnect.telemetry.feed_setting',
                    feed_id=self.feed.id,
                    data_stream_label=data_stream.label
                ),
            },
            'comment_form': comment_form,
            'messages': [
                {
                    'id': message.id,
                    'message_type': message.message_type,
                    'author': (
                        {
                            'id': message.author.id,
                            'name': message.author.email
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
    route_name='sngconnect.telemetry.feed_permissions',
    renderer='sngconnect.telemetry:templates/feed/permissions.jinja2',
    permission='sngconnect.telemetry.access'
)
class FeedPermissions(FeedViewBase):

    def __init__(self, request):
        super(FeedPermissions, self).__init__(request)
        if not self.feed_permissions['can_change_permissions']:
            raise httpexceptions.HTTPForbidden()
        if self.feed_user is None:
            self.can_manage_users = True
        else:
            self.can_manage_users = self.feed_user.role_user
        self.context.update({
            'can_manage_users': self.can_manage_users,
        })

    def __call__(self):
        add_user_form = forms.AddFeedUserForm(
            csrf_context=self.request
        )
        add_maintainer_form = forms.AddFeedMaintainerForm(
            csrf_context=self.request
        )
        if self.request.method == 'POST':
            if 'submit_add_user' in self.request.POST:
                if not self.can_manage_users:
                    raise httpexceptions.HTTPForbidden()
                add_user_form.process(self.request.POST)
                if add_user_form.validate():
                    user = add_user_form.get_user()
                    feed_user_count = DBSession.query(FeedUser).filter(
                        FeedUser.feed == self.feed,
                        FeedUser.user_id == user.id,
                        FeedUser.role_user == True
                    ).count()
                    if feed_user_count > 0:
                        add_user_form.email.errors.append(
                            _("This user already has access to this device.")
                        )
                    else:
                        DBSession.query(User).filter(
                            User.id == user.id,
                        ).update({
                            'role_user': True,
                        })
                        feed_user = FeedUser(
                            feed=self.feed,
                            user_id=user.id,
                            role_user=True
                        )
                        DBSession.add(feed_user)
                        self.request.session.flash(
                            _("User has been successfuly added."),
                            queue='success'
                        )
                        return httpexceptions.HTTPFound(
                            self.request.route_url(
                                'sngconnect.telemetry.feed_permissions',
                                feed_id=self.feed.id
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
            elif 'submit_add_maintainer' in self.request.POST:
                add_maintainer_form.process(self.request.POST)
                if add_maintainer_form.validate():
                    user = add_maintainer_form.get_user()
                    feed_user_count = DBSession.query(FeedUser).filter(
                        FeedUser.feed_id == self.feed.id,
                        FeedUser.user_id == user.id,
                        FeedUser.role_maintainer == True
                    ).count()
                    if feed_user_count > 0:
                        add_maintainer_form.email.errors.append(
                            _(
                                "This maintainer already has access to"
                                " this device."
                            )
                        )
                    else:
                        DBSession.query(User).filter(
                            User.id == user.id,
                        ).update({
                            'role_maintainer': True,
                        })
                        feed_user = FeedUser(
                            user_id=user.id,
                            feed_id=self.feed.id,
                            role_maintainer=True
                        )
                        DBSession.add(feed_user)
                        self.request.session.flash(
                            _("Maintainer has been successfuly added."),
                            queue='success'
                        )
                        return httpexceptions.HTTPFound(
                            self.request.route_url(
                                'sngconnect.telemetry.feed_permissions',
                                feed_id=self.feed.id
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
        base_query = DBSession.query(FeedUser).join(User).options(
            joinedload(FeedUser.user)
        ).filter(
            FeedUser.feed_id == self.feed.id
        ).order_by(User.email)
        feed_users = base_query.filter(
            FeedUser.role_user == True
        ).all()
        feed_maintainers = base_query.filter(
            FeedUser.role_maintainer == True
        ).all()
        self.context.update({
            'feed_users': feed_users,
            'feed_maintainers': feed_maintainers,
            'add_user_form': add_user_form,
            'add_maintainer_form': add_maintainer_form,
        })
        return self.context

    @view_config(
        route_name='sngconnect.telemetry.feed_permissions.set_user_permissions',
        request_method='POST',
        permission='sngconnect.telemetry.access'
    )
    def set_user_permissions(self):
        if not self.can_manage_users:
            raise httpexceptions.HTTPForbidden()
        post_keys = filter(
            lambda x: x.startswith('can_access-'),
            self.request.POST.iterkeys()
        )
        feed_user_ids = []
        for post_key in post_keys:
            try:
                feed_user_ids.append(int(post_key.split('-')[1]))
            except (IndexError, ValueError):
                continue
        DBSession.query(FeedUser).filter(
            FeedUser.feed == self.feed,
            ~FeedUser.id.in_(feed_user_ids),
            FeedUser.user_id != self.user_id,
            FeedUser.role_user == True
        ).delete(synchronize_session=False)
        permission_fields = {
            'can_change_permissions': filter(
                lambda x: x.startswith('can_change_permissions-'),
                self.request.POST.iterkeys()
            ),
        }
        for field_name, post_keys in permission_fields.iteritems():
            feed_user_ids = []
            for post_key in post_keys:
                try:
                    feed_user_ids.append(int(post_key.split('-')[1]))
                except (IndexError, ValueError):
                    continue
            DBSession.query(FeedUser).filter(
                FeedUser.feed == self.feed,
                FeedUser.user_id != self.user_id,
                FeedUser.role_user == True
            ).update({
                field_name: False
            })
            DBSession.query(FeedUser).filter(
                FeedUser.feed == self.feed,
                FeedUser.id.in_(feed_user_ids),
                FeedUser.user_id != self.user_id,
                FeedUser.role_user == True
            ).update({
                field_name: True
            }, synchronize_session=False)
        self.request.session.flash(
            _("User permissions have been successfuly saved."),
            queue='success'
        )
        return httpexceptions.HTTPFound(
            self.request.route_url(
                'sngconnect.telemetry.feed_permissions',
                feed_id=self.feed.id
            )
        )

    @view_config(
        route_name=(
            'sngconnect.telemetry.feed_permissions.set_maintainer_permissions'
        ),
        request_method='POST',
        permission='sngconnect.telemetry.access'
    )
    def set_maintainer_permissions(self):
        post_keys = filter(
            lambda x: x.startswith('can_access-'),
            self.request.POST.iterkeys()
        )
        feed_user_ids = []
        for post_key in post_keys:
            try:
                feed_user_ids.append(int(post_key.split('-')[1]))
            except (IndexError, ValueError):
                continue
        DBSession.query(FeedUser).filter(
            FeedUser.feed == self.feed,
            ~FeedUser.id.in_(feed_user_ids),
            FeedUser.user_id != self.user_id,
            FeedUser.role_maintainer == True
        ).delete(synchronize_session=False)
        permission_fields = {
            'can_change_permissions': filter(
                lambda x: x.startswith('can_change_permissions-'),
                self.request.POST.iterkeys()
            ),
        }
        for field_name, post_keys in permission_fields.iteritems():
            feed_user_ids = []
            for post_key in post_keys:
                try:
                    feed_user_ids.append(int(post_key.split('-')[1]))
                except (IndexError, ValueError):
                    continue
            DBSession.query(FeedUser).filter(
                FeedUser.feed == self.feed,
                FeedUser.user_id != self.user_id,
                FeedUser.role_maintainer == True
            ).update({
                field_name: False
            })
            DBSession.query(FeedUser).filter(
                FeedUser.feed == self.feed,
                FeedUser.id.in_(feed_user_ids),
                FeedUser.user_id != self.user_id,
                FeedUser.role_maintainer == True
            ).update({
                field_name: True
            }, synchronize_session=False)
        self.request.session.flash(
            _("User permissions have been successfuly saved."),
            queue='success'
        )
        return httpexceptions.HTTPFound(
            self.request.route_url(
                'sngconnect.telemetry.feed_permissions',
                feed_id=self.feed.id
            )
        )

@view_config(
    route_name='sngconnect.telemetry.feed_history',
    renderer='sngconnect.telemetry:templates/feed/history.jinja2',
    permission='sngconnect.telemetry.access'
)
class FeedHistory(FeedViewBase):

    def __call__(self):
        message_service = MessageService(self.request)
        comment_form = forms.CommentForm(csrf_context=self.request)
        if self.request.method == 'POST':
            comment_form.process(self.request.POST)
            if comment_form.validate():
                message = Message(
                    message_type='COMMENT',
                    date=pytz.utc.localize(datetime.datetime.utcnow()),
                    feed=self.feed,
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
                        'sngconnect.telemetry.feed_history',
                        feed_id=self.feed.id
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
        user_service = UserService(self.request)
        filter_form = forms.FilterMessagesForm(
            self.feed,
            user_service.get_all_feed_users(self.feed),
            self.feed.template.data_stream_templates,
            message_service,
            self.request.GET
        )
        messages = filter_form.get_messages()
        self.context.update({
            'comment_form': comment_form,
            'filter_form': filter_form,
            'messages': [
                {
                    'id': message.id,
                    'message_type': message.message_type,
                    'data_stream': (
                        {
                            'id': message.data_stream.id,
                            'name': message.data_stream.name,
                            'url': self.request.route_url(
                                (
                                    'sngconnect.telemetry.feed_data_stream'
                                    if not message.data_stream.writable else
                                    'sngconnect.telemetry.feed_settings'
                                ),
                                feed_id=message.data_stream.feed_id,
                                data_stream_label=message.data_stream.label
                            ),
                        }
                        if message.data_stream is not None
                        else None
                    ),
                    'author': (
                        {
                            'id': message.author.id,
                            'name': message.author.email
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
