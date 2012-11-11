# -*- coding: utf-8 -*-

import datetime
import decimal

import pytz
from sqlalchemy.orm import exc as database_exceptions, joinedload
from pyramid.view import view_config
from pyramid import httpexceptions
from pyramid.security import authenticated_userid, has_permission

from sngconnect.translation import _
from sngconnect.database import (DBSession, Feed, DataStreamTemplate,
    DataStream, AlarmDefinition, Message, FeedUser, User)
from sngconnect.cassandra import data_streams as data_streams_store
from sngconnect.cassandra import alarms as alarms_store
from sngconnect.telemetry import forms

@view_config(
    route_name='sngconnect.telemetry.feeds',
    request_method='GET',
    permission='sngconnect.telemetry.access'
)
def feeds(request):
    return httpexceptions.HTTPSeeOther(
        request.route_url('sngconnect.telemetry.dashboard')
    )

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
        self.feed_user = feed_user
        self.feed_permissions = feed_permissions
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
        # FIXME this is very ineffective
        messages = DBSession.query(Message).filter(
            Feed.id == self.feed.id
        ).order_by(
            Message.date
        )
        # TODO: filter only those without data_stream i.e. relating directly to
        # feeds
        error_messages = DBSession.query(Message).filter(
            Feed.id == self.feed.id,
            Message.message_type == u'ERROR'
        ).order_by(
            Message.date
        )
        # TODO: filter only those that were not SEEN or ACKNOWLEDGED by the
        # user currently logged in (simple 'seen' flag in Message is not enough
        # - it has to work per user basis)
        last_updated = (
            data_streams_store.LastDataPoints().get_last_data_stream_datetime(
                self.feed.id
            )
        )
        self.context.update({
            'messages': messages,
            'error_messages': error_messages,
            'last_updated': last_updated
        })
        return self.context

@view_config(
    route_name='sngconnect.telemetry.feed_charts',
    request_method='GET',
    renderer='sngconnect.telemetry:templates/feed/charts.jinja2',
    permission='sngconnect.telemetry.access'
)
class FeedCharts(FeedViewBase):
    pass

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
    renderer='sngconnect.telemetry:templates/feed/data_stream.jinja2',
    permission='sngconnect.telemetry.access'
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
    renderer='sngconnect.telemetry:templates/feed/settings.jinja2',
    permission='sngconnect.telemetry.access'
)
class FeedSettings(FeedViewBase):
    pass

@view_config(
    route_name='sngconnect.telemetry.feed_permissions',
    renderer='sngconnect.telemetry:templates/feed/permissions.jinja2',
    permission='sngconnect.telemetry.access'
)
class FeedPermissions(FeedViewBase):
    def __call__(self):
        if not self.feed_permissions['can_change_permissions']:
            raise httpexceptions.HTTPForbidden()
        if self.feed_user is None:
            can_manage_users = True
        else:
            can_manage_users = self.feed_user.role_user
        add_user_form = forms.AddFeedUserForm(
            csrf_context=self.request
        )
        add_maintainer_form = forms.AddFeedMaintainerForm(
            csrf_context=self.request
        )
        if self.request.method == 'POST':
            if 'submit_save_permissions' in self.request.POST:
                permission_fields = {
                    'can_change_permissions': filter(
                        lambda x: x.startswith('can_change_permissions-'),
                        self.request.POST.iterkeys()
                    )
                }
                for field_name, post_keys in permission_fields.iteritems():
                    feed_user_ids = []
                    for post_key in post_keys:
                        try:
                            feed_user_ids.append(int(post_key.split('-')[1]))
                        except (IndexError, ValueError):
                            continue
                    DBSession.query(FeedUser).filter(
                        FeedUser.user_id != self.user_id
                    ).update({
                        field_name: False
                    })
                    DBSession.query(FeedUser).filter(
                        FeedUser.id.in_(feed_user_ids),
                        FeedUser.user_id != self.user_id
                    ).update({
                        field_name: True
                    }, synchronize_session='fetch')
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
            elif 'submit_add_user' in self.request.POST:
                add_user_form.process(self.request.POST)
                if add_user_form.validate():
                    user = add_user_form.get_user()
                    feed_user_count = DBSession.query(FeedUser).filter(
                        FeedUser.feed_id == self.feed.id,
                        FeedUser.role_user == True
                    ).count()
                    if feed_user_count > 0:
                        add_user_form.email.errors.append(
                            _("This user already has access to this device.")
                        )
                    else:
                        feed_user = FeedUser(
                            user_id=user.id,
                            feed_id=self.feed.id,
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
            'can_manage_users': can_manage_users,
            'add_user_form': add_user_form,
            'add_maintainer_form': add_maintainer_form,
        })
        return self.context

@view_config(
    route_name='sngconnect.telemetry.feed_setting',
    request_method='GET',
    renderer='sngconnect.telemetry:templates/feed/setting.jinja2',
    permission='sngconnect.telemetry.access'
)
class FeedSetting(FeedViewBase):
    pass

@view_config(
    route_name='sngconnect.telemetry.feed_history',
    request_method='GET',
    renderer='sngconnect.telemetry:templates/feed/history.jinja2',
    permission='sngconnect.telemetry.access'
)
class FeedHistory(FeedViewBase):
    pass
