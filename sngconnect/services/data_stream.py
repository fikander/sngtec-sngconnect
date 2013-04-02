import datetime

import pytz
import transaction

from sngconnect.services.base import ServiceBase
from sngconnect.database import DBSession, DataStream

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
        self.request.registry['scheduler'].add_date_job(
            DataStreamService.assert_requested_value,
            datetime.datetime.utcnow() + self._requested_value_timeout,
            [data_stream.id]
        )

    @classmethod
    def assert_requested_value(cls, data_stream_id):
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
