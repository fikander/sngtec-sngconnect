import datetime

import pytz
import transaction

from sngconnect.services.base import ServiceBase
from sngconnect.services.notification import NotificationService
from sngconnect.database import DBSession, DataStream, Message
from sngconnect.translation import _

class DataStreamService(ServiceBase):

    _requested_value_timeout = datetime.timedelta(minutes=15)

    def set_requested_value(self, data_stream, value):
        DBSession.query(DataStream).filter(
            DataStream.id == data_stream.id
        ).update({
            'requested_value': value,
            'value_requested_at': pytz.utc.localize(
                datetime.datetime.utcnow()
            ),
        })
        self.registry['scheduler'].add_date_job(
            DataStreamService.assert_requested_value,
            datetime.datetime.now() + self._requested_value_timeout,
            [self.registry, data_stream.id]
        )

    @classmethod
    def assert_requested_value(cls, registry, data_stream_id):
        data_stream = DBSession.query(DataStream).filter(
            DataStream.id == data_stream_id
        ).one()
        if data_stream is None:
            return
        timeout_time_ago = (
            pytz.utc.localize(datetime.datetime.utcnow())
                - cls._requested_value_timeout
        )
        if (data_stream.requested_value is not None and
                data_stream.value_requested_at <= timeout_time_ago):
            with transaction.manager:
                DBSession.query(DataStream).filter(
                    DataStream.id == data_stream.id
                ).update({
                    'requested_value': None,
                    'value_requested_at': None,
                })
            message = Message(
                feed=data_stream.feed,
                data_stream=data_stream,
                message_type='ERROR',
                date=pytz.utc.localize(datetime.datetime.utcnow()),
                content=_(
                    "${feed_name} did not respond to the request.",
                    mapping={
                        'feed_name': data_stream.feed.name,
                    }
                )
            )
            notification_service = NotificationService(registry)
            with transaction.manager:
                notification_service.notify_feed_users(
                    data_stream.feed,
                    _(
                        "Unable to set parameter ${parameter_name}.",
                        mapping={
                            'parameter_name': data_stream.name
                        }
                    ),
                    message
                )
