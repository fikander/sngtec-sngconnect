# -*- coding: utf-8 -*-

from sqlalchemy.orm import exc as database_exceptions
from pyramid import httpexceptions
from pyramid.security import authenticated_userid, has_permission

from sngconnect.database import (DBSession, Feed, DataStreamTemplate,
    DataStream, FeedUser, User)
from sngconnect.cassandra import alarms as alarms_store

class FeedViewBase(object):

    def __init__(self, request):
        self.user_id = authenticated_userid(request)
        can_access_all = has_permission(
            'sngconnect.telemetry.access_all',
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
            feed_permissions = FeedUser.get_all_permissions()
        else:
            feed_permissions = feed_user.get_permissions()
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
