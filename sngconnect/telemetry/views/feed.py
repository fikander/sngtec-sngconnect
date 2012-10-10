# -*- coding: utf-8 -*-

import datetime
import decimal

import pytz
from sqlalchemy.orm import exc as database_exceptions
from pyramid.view import view_config
from pyramid import httpexceptions

from sngconnect.database import (DBSession, Feed, DataStreamTemplate,
    DataStream, AlarmDefinition)
from sngconnect.cassandra import data_streams as data_streams_store
from sngconnect.cassandra import alarms as alarms_store

@view_config(
    route_name='sngconnect.telemetry.feeds',
    request_method='GET'
)
def feeds(request):
    raise httpexceptions.HTTPSeeOther(
        request.route_url('sngconnect.telemetry.dashboard')
    )

class FeedViewBase(object):

    def __init__(self, request):
        try:
            feed = DBSession.query(Feed).filter(
                Feed.id == request.matchdict['feed_id']
            ).one()
        except database_exceptions.NoResultFound:
            raise httpexceptions.HTTPNotFound()
        self.request = request
        self.feed = feed
        # FIXME getting alarms out is kind of dumb
        result = alarms_store.Alarms().get_active_alarms(feed.id)
        active_alarms = []
        for data_stream_id, alarms in result:
            data_stream = DataStream(id=data_stream_id)
            for definition_id, activation_date in alarms:
                definition = AlarmDefinition(id=definition_id)
                active_alarms.append({
                    'activation_date': activation_date,
                    'data_stream': data_stream.name,
                    'type': definition.alarm_type,
                })
        self.context = {
            'active_alarms': active_alarms,
            'feed': {
                'id': feed.id,
                'name': feed.name,
                'description': feed.description,
                'address': feed.address,
                'latitude': feed.latitude,
                'longitude': feed.longitude,
                'created': feed.created,
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
                'history_url': request.route_url(
                    'sngconnect.telemetry.feed_history',
                    feed_id=feed.id
                ),
            }
        }

    def __call__(self):
        return self.context

@view_config(
    route_name='sngconnect.telemetry.feed_dashboard',
    request_method='GET',
    renderer='sngconnect.telemetry:templates/feed/dashboard.jinja2'
)
class FeedDashboard(FeedViewBase):
    pass

@view_config(
    route_name='sngconnect.telemetry.feed_charts',
    request_method='GET',
    renderer='sngconnect.telemetry:templates/feed/charts.jinja2'
)
class FeedCharts(FeedViewBase):
    pass

@view_config(
    route_name='sngconnect.telemetry.feed_data_streams',
    request_method='GET',
    renderer='sngconnect.telemetry:templates/feed/data_streams.jinja2'
)
class FeedDataStreams(FeedViewBase):
    def __call__(self):
        data_streams = DBSession.query(DataStream).join(
            DataStreamTemplate
        ).filter(
            Feed.id == self.feed.id
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
    request_method='GET',
    renderer='sngconnect.telemetry:templates/feed/data_stream.jinja2'
)
class FeedDataStream(FeedViewBase):
    def __call__(self):
        try:
            data_stream = DBSession.query(DataStream).join(
                DataStreamTemplate
            ).filter(
                Feed.id == self.feed.id,
                (DataStreamTemplate.label ==
                    self.request.matchdict['data_stream_label'])
            ).one()
        except database_exceptions.NoResultFound:
            raise httpexceptions.HTTPNotFound()
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
        last_data_point = (
            data_streams_store.LastDataPoints().get_last_data_stream_data_point(
                self.feed.id,
                data_stream.id
            )
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
        self.context.update({
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
        })
        return self.context

@view_config(
    route_name='sngconnect.telemetry.feed_settings',
    request_method='GET',
    renderer='sngconnect.telemetry:templates/feed/settings.jinja2'
)
class FeedSettings(FeedViewBase):
    pass

@view_config(
    route_name='sngconnect.telemetry.feed_setting',
    request_method='GET',
    renderer='sngconnect.telemetry:templates/feed/setting.jinja2'
)
class FeedSetting(FeedViewBase):
    pass

@view_config(
    route_name='sngconnect.telemetry.feed_history',
    request_method='GET',
    renderer='sngconnect.telemetry:templates/feed/history.jinja2'
)
class FeedHistory(FeedViewBase):
    pass
