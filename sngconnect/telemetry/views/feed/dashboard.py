# -*- coding: utf-8 -*-

import datetime
import decimal
import json

import pytz
from sqlalchemy.orm import exc as database_exceptions, joinedload
from pyramid.response import Response
from pyramid.view import view_config
from pyramid import httpexceptions
from pyramid.i18n import get_locale_name

from sngconnect.database import (DBSession, DataStreamTemplate, DataStream,
    AlarmDefinition, ChartDefinition)
from sngconnect.services.message import MessageService
from sngconnect.services.data_stream import DataStreamService
from sngconnect.cassandra import data_streams as data_streams_store
from sngconnect.telemetry import forms
from sngconnect.telemetry.views.feed.base import FeedViewBase

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
        message_service = MessageService(self.request.registry)
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
                            'minimum': template.default_minimum,
                            'maximum': template.default_maximum,
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
                data_stream_service = DataStreamService(self.request.registry)
                data_stream_service.set_requested_value(
                    data_stream,
                    value_form.value.data
                )
                return Response(
                    json.dumps({'success': True}),
                    content_type='application/json'
                )
        return Response(
            json.dumps({'success': False}),
            content_type='application/json'
        )
