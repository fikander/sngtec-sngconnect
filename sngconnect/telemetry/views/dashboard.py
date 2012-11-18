# -*- coding: utf-8 -*-

from pyramid.view import view_config
from pyramid.security import authenticated_userid

from sngconnect.database import DBSession, Feed
from sngconnect.cassandra import alarms as alarms_store

@view_config(
    route_name='sngconnect.telemetry.dashboard',
    request_method='GET',
    renderer='sngconnect.telemetry:templates/dashboard.jinja2',
    permission='sngconnect.telemetry.access'
)
def dashboard(request):
    user_id = authenticated_userid(request)
    feeds = DBSession.query(Feed).filter(
        Feed.feed_users.any(user_id=user_id)
    ).order_by(Feed.name)
    serialized_feeds = []
    feeds_with_alarm_active = 0
    for feed in feeds:
        active_alarms = alarms_store.Alarms().get_active_alarms(feed.id)
        active_alarm_count = sum(
            map(len, active_alarms.itervalues())
        )
        if active_alarm_count > 0:
            feeds_with_alarm_active += 1
        serialized_feeds.append({
            'id': feed.id,
            'name': feed.name,
            'latitude': feed.latitude,
            'longitude': feed.longitude,
            'template_name': feed.template_name,
            'dashboard_url': request.route_url(
                'sngconnect.telemetry.feed_dashboard',
                feed_id=feed.id
            ),
            'active_alarm_count': active_alarm_count,
        })
    return {
        'feeds_with_alarm_active': feeds_with_alarm_active,
        'feeds': serialized_feeds,
    }
