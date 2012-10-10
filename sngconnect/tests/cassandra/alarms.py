import unittest
import datetime

import pytz

from sngconnect.cassandra import alarms

from sngconnect.tests.cassandra import CassandraTestMixin

def _utc_datetime(*datetime_tuple):
    return pytz.utc.localize(datetime.datetime(*datetime_tuple))

class TestAlarms(CassandraTestMixin, unittest.TestCase):

    def setUp(self):
        super(TestAlarms, self).setUp()
        self.alarms = alarms.Alarms()

    def test_basic_operation(self):
        feed_id = 24355
        data_stream_id = 2342342
        data_stream2_id = 234348
        active_alarms = self.alarms.get_active_alarms(feed_id)
        self.assertDictEqual(active_alarms, {})
        active_alarms = self.alarms.get_active_alarms(feed_id, data_stream_id)
        self.assertDictEqual(active_alarms, {})
        self.alarms.set_alarms_off(feed_id, data_stream_id, [12, 13, 14])
        active_alarms = self.alarms.get_active_alarms(feed_id)
        self.assertDictEqual(active_alarms, {})
        date = _utc_datetime(2012, 10, 8, 14, 11, 5, 344008)
        self.alarms.set_alarms_on(
            feed_id,
            data_stream_id,
            [12, 1, 13234],
            date
        )
        active_alarms = self.alarms.get_active_alarms(feed_id)
        self.assertDictEqual(active_alarms, {
            data_stream_id: {
                1: date,
                12: date,
                13234: date,
            },
        })
        active_alarms = self.alarms.get_active_alarms(feed_id, data_stream_id)
        self.assertDictEqual(active_alarms, {
            1: date,
            12: date,
            13234: date,
        })
        self.alarms.set_alarms_on(
            feed_id,
            data_stream2_id,
            [32],
            date
        )
        active_alarms = self.alarms.get_active_alarms(feed_id)
        self.assertDictEqual(active_alarms, {
            data_stream_id: {
                1: date,
                12: date,
                13234: date,
            },
            data_stream2_id: {
                32: date,
            },
        })
        active_alarms = self.alarms.get_active_alarms(feed_id, data_stream_id)
        self.assertDictEqual(active_alarms, {
            1: date,
            12: date,
            13234: date,
        })
        active_alarms = self.alarms.get_active_alarms(feed_id, data_stream2_id)
        self.assertDictEqual(active_alarms, {
            32: date,
        })
        self.alarms.set_alarms_off(feed_id, data_stream_id, [12])
        active_alarms = self.alarms.get_active_alarms(feed_id, data_stream_id)
        self.assertDictEqual(active_alarms, {
            1: date,
            13234: date,
        })
        self.alarms.set_alarms_off(feed_id, data_stream2_id, [12])
        active_alarms = self.alarms.get_active_alarms(feed_id, data_stream2_id)
        self.assertDictEqual(active_alarms, {
            32: date,
        })
        self.alarms.set_alarms_off(feed_id, data_stream2_id, [32])
        active_alarms = self.alarms.get_active_alarms(feed_id, data_stream2_id)
        self.assertDictEqual(active_alarms, {})
