import os
import gzip
import csv
import unittest
import datetime

import pytz
import isodate

from sngconnect.cassandra import data_streams

from sngconnect.tests.cassandra import CassandraTestMixin

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


def _utc_datetime(*datetime_tuple):
    return pytz.utc.localize(datetime.datetime(*datetime_tuple))


def _get_test_data_points():
    reader = csv.reader(
        gzip.open(os.path.join(TEST_DATA_DIR, 'data_points.csv.gz'), 'r')
    )
    return (
        (
            isodate.parse_datetime(date_iso),
            value
        )
        for date_iso, value in reader
    )


def _dp(datetime_tuple, decimal_string):
    """Takes care of data point types."""
    return (
        _utc_datetime(*datetime_tuple),
        decimal_string
    )


def _dpa(datetime_tuple, aggregate_mapping):
    """Takes care of data point aggregate types."""
    return (
        _utc_datetime(*datetime_tuple),
        aggregate_mapping
    )


class TestMeasurementDays(CassandraTestMixin, unittest.TestCase):

    def setUp(self):
        super(TestMeasurementDays, self).setUp()
        self.measurement_days = data_streams.MeasurementDays()

    def test_basic_operation(self):
        data_stream_id = 12245
        self.assertSequenceEqual(
            self.measurement_days.get_days(data_stream_id),
            []
        )
        self.assertEqual(
            self.measurement_days.get_last_day(data_stream_id),
            None
        )
        dates = [
            _utc_datetime(2012, 9, 11, 15, 18, 54),
            _utc_datetime(2012, 9, 15, 22,  0, 07),
            _utc_datetime(2012, 9, 18,  9, 12,  0),
            _utc_datetime(2012, 9, 19,  0,  0,  0),
        ]
        self.measurement_days.add_days(data_stream_id, dates)
        self.assertSequenceEqual(
            self.measurement_days.get_days(data_stream_id),
            [
                _utc_datetime(2012, 9, 11),
                _utc_datetime(2012, 9, 15),
                _utc_datetime(2012, 9, 18),
                _utc_datetime(2012, 9, 19),
            ]
        )
        self.assertEqual(
            self.measurement_days.get_last_day(data_stream_id),
            _utc_datetime(2012, 9, 19)
        )
        self.assertEqual(
            self.measurement_days.get_last_day(data_stream_id + 9),
            None
        )
        self.assertSequenceEqual(
            self.measurement_days.get_days(data_stream_id + 13),
            []
        )
        self.measurement_days.add_days(data_stream_id, [
            _utc_datetime(2012, 9, 15, 22,  0, 07),
            _utc_datetime(2012, 7, 20, 23, 59, 59),
            _utc_datetime(2012, 9, 18,  8,  9, 17),
            _utc_datetime(2012, 7, 20, 23, 59, 59),
        ])
        self.assertSequenceEqual(
            self.measurement_days.get_days(data_stream_id),
            [
                _utc_datetime(2012, 7, 20),
                _utc_datetime(2012, 9, 11),
                _utc_datetime(2012, 9, 15),
                _utc_datetime(2012, 9, 18),
                _utc_datetime(2012, 9, 19),
            ]
        )
        self.assertEqual(
            self.measurement_days.get_last_day(data_stream_id),
            _utc_datetime(2012, 9, 19)
        )
        self.assertSequenceEqual(
            self.measurement_days.get_days(data_stream_id + 1),
            []
        )


class TestHourlyAggregates(CassandraTestMixin, unittest.TestCase):

    def setUp(self):
        super(TestHourlyAggregates, self).setUp()
        self.measurements = data_streams.Measurements()
        self.hourly_aggregates = data_streams.HourlyAggregates()

    def test_basic_operation(self):
        data_stream_id = 3423423
        data_points = list(_get_test_data_points())
        self.measurements.insert_data_points(
            data_stream_id,
            # Shuffled to ensure database ordering.
            data_points[500:] + data_points[:500]
        )
        aggregates = self.hourly_aggregates.get_data_points(data_stream_id)
        self.assertAggregatesEqual(aggregates, [])
        self.hourly_aggregates.recalculate_aggregates(data_stream_id, [
            date for date, value in data_points
        ])
        hourly_aggregates_data = list(sorted([
            (
                isodate.parse_datetime(date_iso),
                {
                    'minimum': minimum,
                    'maximum': maximum,
                    'sum': sum,
                    'count': count,
                }
            )
            for date_iso, minimum, maximum, sum, count
            in csv.reader(
                gzip.open(
                    os.path.join(TEST_DATA_DIR, 'hourly_aggregates.csv.gz'),
                    'r'
                )
            )
        ], key=lambda x: x[0]))
        aggregates = self.hourly_aggregates.get_data_points(data_stream_id)
        self.assertAggregatesEqual(
            aggregates,
            hourly_aggregates_data
        )
        aggregates = self.hourly_aggregates.get_data_points(
            data_stream_id,
            start_date=_utc_datetime(2012, 9, 24, 12),
            end_date=_utc_datetime(2012, 9, 24, 13)
        )
        self.assertAggregatesEqual(
            aggregates,
            (
                _dpa((2012, 9, 24, 12), {
                    'minimum': '-24.1510049289',
                    'maximum': '19.0748727824',
                    'sum': '-241.750415083',
                    'count': '81',
                }),
                _dpa((2012, 9, 24, 13), {
                    'minimum': '-26.3652634393',
                    'maximum': '21.6779082413',
                    'sum': '-28.1296171473',
                    'count': '121',
                }),
            )
        )
        aggregates = self.hourly_aggregates.get_data_points(data_stream_id + 2)
        self.assertAggregatesEqual(aggregates, [])


class TestDailyAggregates(CassandraTestMixin, unittest.TestCase):

    def setUp(self):
        super(TestDailyAggregates, self).setUp()
        self.measurements = data_streams.Measurements()
        self.hourly_aggregates = data_streams.HourlyAggregates()
        self.daily_aggregates = data_streams.DailyAggregates()

    def test_basic_operation(self):
        data_stream_id = 23555
        data_points = list(_get_test_data_points())
        self.measurements.insert_data_points(
            data_stream_id,
            # Shuffled to ensure database ordering.
            data_points[500:] + data_points[:500]
        )
        aggregates = self.daily_aggregates.get_data_points(data_stream_id)
        self.assertAggregatesEqual(aggregates, [])
        self.hourly_aggregates.recalculate_aggregates(data_stream_id, [
            date for date, value in data_points
        ])
        self.daily_aggregates.recalculate_aggregates(data_stream_id, [
            date for date, value in data_points
        ])
        daily_aggregates_data = list(sorted([
            (
                isodate.parse_datetime(date_iso),
                {
                    'minimum': minimum,
                    'maximum': maximum,
                    'sum': sum,
                    'count': count,
                }
            )
            for date_iso, minimum, maximum, sum, count
            in csv.reader(
                gzip.open(
                    os.path.join(TEST_DATA_DIR, 'daily_aggregates.csv.gz'),
                    'r'
                )
            )
        ], key=lambda x: x[0]))
        aggregates = self.daily_aggregates.get_data_points(data_stream_id)
        self.assertAggregatesEqual(
            aggregates,
            daily_aggregates_data
        )
        aggregates = self.daily_aggregates.get_data_points(
            data_stream_id,
            start_date=_utc_datetime(2012, 9, 24),
            end_date=_utc_datetime(2012, 9, 25)
        )
        self.assertAggregatesEqual(
            aggregates,
            (
                _dpa((2012, 9, 24), {
                    'minimum': '-34.1889758363',
                    'maximum': '34.0196311155',
                    'sum': '-741.140138924',
                    'count': '1374',
                }),
                _dpa((2012, 9, 25), {
                    'minimum': '-42.9091583044',
                    'maximum': '33.9159915355',
                    'sum': '-3098.25337205',
                    'count': '2862',
                }),
            )
        )
        aggregates = self.daily_aggregates.get_data_points(data_stream_id + 2)
        self.assertAggregatesEqual(aggregates, [])


class TestMonthlyAggregates(CassandraTestMixin, unittest.TestCase):

    def setUp(self):
        super(TestMonthlyAggregates, self).setUp()
        self.measurements = data_streams.Measurements()
        self.hourly_aggregates = data_streams.HourlyAggregates()
        self.daily_aggregates = data_streams.DailyAggregates()
        self.monthly_aggregates = data_streams.MonthlyAggregates()

    def test_basic_operation(self):
        data_stream_id = 23555
        data_points = list(_get_test_data_points())
        self.measurements.insert_data_points(
            data_stream_id,
            # Shuffled to ensure database ordering.
            data_points[500:] + data_points[:500]
        )
        aggregates = self.monthly_aggregates.get_data_points(data_stream_id)
        self.assertAggregatesEqual(aggregates, [])
        self.hourly_aggregates.recalculate_aggregates(data_stream_id, [
            date for date, value in data_points
        ])
        self.daily_aggregates.recalculate_aggregates(data_stream_id, [
            date for date, value in data_points
        ])
        self.monthly_aggregates.recalculate_aggregates(data_stream_id, [
            date for date, value in data_points
        ])
        monthly_aggregates_data = list(sorted([
            (
                isodate.parse_datetime(date_iso),
                {
                    'minimum': minimum,
                    'maximum': maximum,
                    'sum': sum,
                    'count': count,
                }
            )
            for date_iso, minimum, maximum, sum, count
            in csv.reader(
                gzip.open(
                    os.path.join(TEST_DATA_DIR, 'monthly_aggregates.csv.gz'),
                    'r'
                )
            )
        ], key=lambda x: x[0]))
        aggregates = self.monthly_aggregates.get_data_points(data_stream_id)
        self.assertAggregatesEqual(
            aggregates,
            monthly_aggregates_data
        )
        aggregates = self.monthly_aggregates.get_data_points(
            data_stream_id,
            start_date=_utc_datetime(2012, 9, 1),
            end_date=_utc_datetime(2012, 9, 1)
        )
        self.assertAggregatesEqual(
            aggregates,
            (
                _dpa((2012, 9, 1), {
                    'minimum': '-42.9091583044',
                    'maximum': '34.0196311155',
                    'sum': '-5758.58206586',
                    'count': '5726',
                }),
            )
        )
        aggregates = self.monthly_aggregates.get_data_points(data_stream_id + 2)
        self.assertAggregatesEqual(aggregates, [])


class TestMeasurements(CassandraTestMixin, unittest.TestCase):

    def setUp(self):
        super(TestMeasurements, self).setUp()
        self.measurements = data_streams.Measurements()

    def test_basic_operation(self):
        data_stream_id = 1253353566
        self.assertSequenceEqual(
            self.measurements.get_data_points(data_stream_id),
            []
        )
        self.assertEqual(
            self.measurements.get_last_data_point(data_stream_id),
            None
        )
        data_points = list(_get_test_data_points())
        self.measurements.insert_data_points(
            data_stream_id,
            # Shuffled to ensure database ordering.
            data_points[500:] + data_points[:500]
        )
        self.assertEqual(
            self.measurements.get_last_data_point(data_stream_id + 2),
            None
        )
        self.assertSequenceEqual(
            self.measurements.get_data_points(data_stream_id + 1),
            []
        )
        self.assertSequenceEqual(
            self.measurements.get_last_data_point(data_stream_id),
            _dp((2012, 9, 26, 12, 17, 25, 739851), '11.207354924')
        )
        self.assertSequenceEqual(
            self.measurements.get_data_points(data_stream_id),
            list(reversed(data_points))
        )
        self.assertSequenceEqual(
            self.measurements.get_data_points(
                data_stream_id,
                start_date=_utc_datetime(2012, 9, 26, 11, 18),
                end_date=_utc_datetime(2012, 9, 26, 11, 18, 34)
            ),
            (
                _dp((2012, 9, 26, 11, 18, 0, 379482), '-22.7874213891'),
                _dp((2012, 9, 26, 11, 18, 33, 835339), '-10.5035473919'),
            )
        )
        self.assertSequenceEqual(
            self.measurements.get_data_points(
                data_stream_id,
                start_date=_utc_datetime(2015, 9, 26, 11, 19),
                end_date=_utc_datetime(2020, 9, 26, 11, 19, 27)
            ),
            []
        )
        self.assertSequenceEqual(
            self.measurements.get_data_points(
                data_stream_id,
                start_date=_utc_datetime(2015, 9, 26, 11, 19),
                end_date=_utc_datetime(2020, 9, 26, 11, 19, 27)
            ),
            []
        )

    def test_remove_data_point(self):
        data_stream_id = 1253353566
        dt = pytz.utc.localize(datetime.datetime(2013, 6, 16, 16, 16, 16, 0))
        self.measurements.insert_data_points(
            data_stream_id,
            [(dt, 999)]
        )
        self.assertSequenceEqual(
            self.measurements.get_data_points(
                data_stream_id, start_date=dt, end_date=dt),
            [(dt, '999')]
        )
        self.measurements.remove_data_point(data_stream_id, dt)
        self.assertSequenceEqual(
            self.measurements.get_data_points(
                data_stream_id, start_date=dt, end_date=dt),
            []
        )

    def test_timezone_support(self):
        data_stream_id = 1253353566
        self.measurements.insert_data_points(
            data_stream_id,
            (
                (
                    pytz.timezone('Europe/Warsaw').localize(
                        datetime.datetime(2012, 9, 28, 17, 35, 12, 543123)
                    ),
                    '3543.44555'
                ),
                (
                    pytz.timezone('Australia/Melbourne').localize(
                        datetime.datetime(2012, 10, 28, 19, 13, 4, 17)
                    ),
                    '-24444.45'
                ),
                (
                    pytz.timezone('Asia/Qyzylorda').localize(
                        datetime.datetime(2011, 12, 1, 9, 59, 59, 999999)
                    ),
                    '0.000002'
                ),
                (
                    pytz.timezone('Pacific/Samoa').localize(
                        datetime.datetime(2012, 9, 1, 23, 59, 59, 999999)
                    ),
                    '0.1'
                ),
            )
        )
        self.assertSequenceEqual(
            self.measurements.get_data_points(data_stream_id),
            (
                (_utc_datetime(2011, 12, 1, 3, 59, 59, 999999), '0.000002'),
                (_utc_datetime(2012, 9, 2, 10, 59, 59, 999999), '0.1'),
                (_utc_datetime(2012, 9, 28, 15, 35, 12, 543123), '3543.44555'),
                (_utc_datetime(2012, 10, 28, 8, 13, 4, 17), '-24444.45'),
            )
        )
        self.assertSequenceEqual(
            self.measurements.get_data_points(
                data_stream_id,
                start_date=_utc_datetime(2012, 9, 2, 10),
                end_date=_utc_datetime(2012, 9, 2, 12)
            ),
            (
                (_utc_datetime(2012, 9, 2, 10, 59, 59, 999999), '0.1'),
            )
        )


class TestLastDataPoints(CassandraTestMixin, unittest.TestCase):

    def setUp(self):
        super(TestLastDataPoints, self).setUp()
        self.measurements = data_streams.Measurements()
        self.last_data_points = data_streams.LastDataPoints()

    def test_basic_operation(self):
        feed_id = 23455
        data_stream_id = 1253353566
        self.assertDictEqual(
            self.last_data_points.get_last_data_stream_data_points(feed_id),
            {}
        )
        self.assertEqual(
            self.last_data_points.get_last_data_stream_data_point(
                feed_id,
                data_stream_id
            ),
            None
        )
        self.measurements.insert_data_points(
            data_stream_id,
            [
                _dp((2012, 12, 8, 11, 45, 9, 123384), '2344.421'),
                _dp((2012,  7, 1,  9, 45, 9, 123383), '2344.421'),
                _dp((2012, 12, 8, 11, 45, 9, 123383), '2344.421'),
            ]
        )
        self.last_data_points.update(feed_id, data_stream_id)
        self.assertDictEqual(
            self.last_data_points.get_last_data_stream_data_points(feed_id),
            {
                data_stream_id: _dp((2012, 12, 8, 11, 45, 9, 123384), '2344.421')
            }
        )
        self.assertEqual(
            self.last_data_points.get_last_data_stream_data_point(
                feed_id,
                data_stream_id
            ),
            _dp((2012, 12, 8, 11, 45, 9, 123384), '2344.421')
        )
        self.measurements.insert_data_points(
            data_stream_id,
            [
                _dp((2012, 12, 9, 11,  0, 9,      0), '15.3'),
                _dp((2013,  7, 4, 23,  0, 1,     87), '2344.421'),
                _dp((2012, 12, 8, 11, 45, 9, 123383), '2344.421'),
            ]
        )
        self.last_data_points.update(feed_id, data_stream_id)
        self.assertDictEqual(
            self.last_data_points.get_last_data_stream_data_points(feed_id),
            {
                data_stream_id: _dp((2013, 7, 4, 23, 0, 1, 87), '2344.421')
            }
        )
        self.assertEqual(
            self.last_data_points.get_last_data_stream_data_point(
                feed_id,
                data_stream_id
            ),
            _dp((2013,  7, 4, 23,  0, 1,     87), '2344.421')
        )
