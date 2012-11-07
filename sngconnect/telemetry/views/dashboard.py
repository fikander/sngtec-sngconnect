# -*- coding: utf-8 -*-

from pyramid.view import view_config
from pyramid.security import authenticated_userid

from sngconnect.database import DBSession, Feed

@view_config(
    route_name='sngconnect.telemetry.dashboard',
    request_method='GET',
    renderer='sngconnect.telemetry:templates/dashboard.jinja2',
    permission='sngconnect.telemetry.access'
)
def dashboard(request):
    user_id = authenticated_userid(request)
    feeds = DBSession.query(Feed).filter(
        Feed.users.any(id=user_id)
    ).order_by(Feed.name)
    return {
        'feeds_with_alarm_active': 2, # FIXME
        'feeds': [
            {
                'id': feed.id,
                'name': feed.name,
                'latitude': feed.latitude,
                'longitude': feed.longitude,
                'dashboard_url': request.route_url(
                    'sngconnect.telemetry.feed_dashboard',
                    feed_id=feed.id
                ),
                # FIXME
                'alarm_count': 5,
                'feed': u"water pump",
                'owner': u"Some owner",
            }
            for feed in feeds
        ],
    }
