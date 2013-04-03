import datetime
import operator

import pytz
import transaction

from sngconnect.cassandra.data_streams import LastDataPoints
from sngconnect.services.base import ServiceBase
from sngconnect.services.notification import NotificationService
from sngconnect.database import DBSession, Feed, Message
from sngconnect.translation import _

class FeedService(ServiceBase):

    _last_update_timeout = datetime.timedelta(days=1)

    @classmethod
    def assert_last_update(cls, registry):
        last_data_points = LastDataPoints()
        now = pytz.utc.localize(datetime.datetime.utcnow())
        timeout_time_ago = now - cls._last_update_timeout
        for feed in DBSession.query(Feed):
            try:
                last_update = max(map(
                    operator.itemgetter(0),
                    last_data_points.get_last_data_stream_data_points(
                        feed.id
                    ).values()
                ))
            except ValueError:
                continue
            if last_update <= timeout_time_ago:
                message = Message(
                    feed=feed,
                    message_type='WARNING',
                    date=now,
                    content=_(
                        "${feed_name} was last updated on ${last_update}.",
                        mapping={
                            'feed_name': feed.name,
                            'last_update': last_update.isoformat(),
                        }
                    )
                )
                notification_service = NotificationService(registry)
                with transaction.manager:
                    notification_service.notify_feed_users(
                        feed,
                        _(
                            "${feed_name} hasn't been updated in a while.",
                            mapping={
                                'feed_name': feed.name,
                            }
                        ),
                        message
                    )
