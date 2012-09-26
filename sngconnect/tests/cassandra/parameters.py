import os
import gzip
import csv
import unittest
import datetime

import isodate

from sngconnect.cassandra import parameters

from sngconnect.tests.cassandra import CassandraTestMixin

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

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
        datetime.datetime(*datetime_tuple),
        decimal_string
    )

def _dpa(datetime_tuple, aggregate_mapping):
    """Takes care of data point aggregate types."""
    return (
        datetime.datetime(*datetime_tuple),
        aggregate_mapping
    )

class TestMeasurementDays(CassandraTestMixin, unittest.TestCase):

    def setUp(self):
        super(TestMeasurementDays, self).setUp()
        self.measurement_days = parameters.MeasurementDays()

    def test_basic_operation(self):
        parameter_id = 12245
        self.assertSequenceEqual(
            self.measurement_days.get_days(parameter_id),
            []
        )
        dates = [
            datetime.datetime(2012, 9, 11, 15, 18, 54),
            datetime.datetime(2012, 9, 15, 22,  0, 07),
            datetime.datetime(2012, 9, 18,  9, 12,  0),
            datetime.datetime(2012, 9, 19,  0,  0,  0),
        ]
        self.measurement_days.add_days(parameter_id, dates)
        self.assertSequenceEqual(
            self.measurement_days.get_days(parameter_id),
            [
                datetime.date(2012, 9, 11),
                datetime.date(2012, 9, 15),
                datetime.date(2012, 9, 18),
                datetime.date(2012, 9, 19),
            ]
        )
        self.assertSequenceEqual(
            self.measurement_days.get_days(parameter_id + 13),
            []
        )
        self.measurement_days.add_days(parameter_id, [
            datetime.datetime(2012, 9, 15, 22,  0, 07),
            datetime.datetime(2012, 7, 20, 23, 59, 59),
            datetime.datetime(2012, 9, 18,  8,  9, 17),
            datetime.datetime(2012, 7, 20, 23, 59, 59),
        ])
        self.assertSequenceEqual(
            self.measurement_days.get_days(parameter_id),
            [
                datetime.date(2012, 7, 20),
                datetime.date(2012, 9, 11),
                datetime.date(2012, 9, 15),
                datetime.date(2012, 9, 18),
                datetime.date(2012, 9, 19),
            ]
        )
        self.assertSequenceEqual(
            self.measurement_days.get_days(parameter_id + 1),
            []
        )

class TestHourlyAggregates(CassandraTestMixin, unittest.TestCase):

    def setUp(self):
        super(TestHourlyAggregates, self).setUp()
        self.measurements = parameters.Measurements()
        self.hourly_aggregates = parameters.HourlyAggregates()

    def test_basic_operation(self):
        parameter_id = 3423423
        data_points = list(_get_test_data_points())
        self.measurements.insert_data_points(
            parameter_id,
            # Shuffled to ensure database ordering.
            data_points[500:] + data_points[:500]
        )
        aggregates = self.hourly_aggregates.get_data_points(parameter_id)
        self.assertAggregatesEqual(aggregates, [])
        self.hourly_aggregates.recalculate_aggregates(parameter_id, [
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
        aggregates = self.hourly_aggregates.get_data_points(parameter_id)
        self.assertAggregatesEqual(
            aggregates,
            hourly_aggregates_data
        )
        aggregates = self.hourly_aggregates.get_data_points(
            parameter_id,
            start_date=datetime.datetime(2012, 9, 24, 12),
            end_date=datetime.datetime(2012, 9, 24, 13)
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
        aggregates = self.hourly_aggregates.get_data_points(parameter_id + 2)
        self.assertAggregatesEqual(aggregates, [])

class TestDailyAggregates(CassandraTestMixin, unittest.TestCase):

    def setUp(self):
        super(TestDailyAggregates, self).setUp()
        self.measurements = parameters.Measurements()
        self.hourly_aggregates = parameters.HourlyAggregates()
        self.daily_aggregates = parameters.DailyAggregates()

    def test_basic_operation(self):
        parameter_id = 23555
        data_points = list(_get_test_data_points())
        self.measurements.insert_data_points(
            parameter_id,
            # Shuffled to ensure database ordering.
            data_points[500:] + data_points[:500]
        )
        aggregates = self.daily_aggregates.get_data_points(parameter_id)
        self.assertAggregatesEqual(aggregates, [])
        self.hourly_aggregates.recalculate_aggregates(parameter_id, [
            date for date, value in data_points
        ])
        self.daily_aggregates.recalculate_aggregates(parameter_id, [
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
        aggregates = self.daily_aggregates.get_data_points(parameter_id)
        self.assertAggregatesEqual(
            aggregates,
            daily_aggregates_data
        )
        aggregates = self.daily_aggregates.get_data_points(
            parameter_id,
            start_date=datetime.datetime(2012, 9, 24),
            end_date=datetime.datetime(2012, 9, 25)
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
        aggregates = self.daily_aggregates.get_data_points(parameter_id + 2)
        self.assertAggregatesEqual(aggregates, [])

#        data_points = [
#            _dp((2012,  9, 21, 23, 59, 59, 999999), '522.343445'),
#            _dp((2012,  9, 22, 15, 11, 12,      0), '4.343445'),
#            _dp((2012,  9, 22,  9, 15,  5,   8001), '23454.0000018'),
#            _dp((2012,  9, 22, 15, 43, 12, 300144), '324255.12'),
#        ]
#        self.measurements.insert_data_points(parameter_id, data_points)
#        changed_dates = [date for date, value in data_points]
#        self.hourly_aggregates.recalculate_aggregates(parameter_id, changed_dates)
#        self.daily_aggregates.recalculate_aggregates(parameter_id, changed_dates)
#        aggregates = self.daily_aggregates.get_data_points(
#            parameter_id,
#            start_date=datetime.datetime(2012, 9, 22)
#        )
#        self.assertAggregatesEqual(aggregates, [
#            _dpa((2012, 9, 22), {
#                'minimum': '4.343445',
#                'maximum': '324255.12',
#                'sum': '347713.4634468',
#                'count': '3',
#            }),
#        ])
#        aggregates = self.daily_aggregates.get_data_points(
#            parameter_id,
#            start_date=datetime.datetime(2018, 1, 12),
#            end_date=datetime.datetime(5000, 12, 8)
#        )
#        self.assertAggregatesEqual(aggregates, [])

class TestMonthlyAggregates(CassandraTestMixin, unittest.TestCase):

    def setUp(self):
        super(TestMonthlyAggregates, self).setUp()
        self.measurements = parameters.Measurements()
        self.hourly_aggregates = parameters.HourlyAggregates()
        self.daily_aggregates = parameters.DailyAggregates()
        self.monthly_aggregates = parameters.MonthlyAggregates()

    def test_basic_operation(self):
        parameter_id = 23555
        data_points = [
            _dp((2012,  9, 21, 23, 59, 59, 999999), '522.343445'),
            _dp((2012,  9, 22, 15, 11, 12,      0), '4.343445'),
            _dp((2012,  9, 22,  9, 15,  5,   8001), '23454.0000018'),
            _dp((2012,  9, 22, 15, 43, 12, 300144), '324255.12'),
        ]
        self.measurements.insert_data_points(parameter_id, data_points)
        changed_dates = [date for date, value in data_points]
        self.hourly_aggregates.recalculate_aggregates(parameter_id, changed_dates)
        self.daily_aggregates.recalculate_aggregates(parameter_id, changed_dates)
        self.monthly_aggregates.recalculate_aggregates(parameter_id, changed_dates)
        aggregates = self.monthly_aggregates.get_data_points(
            parameter_id,
            start_date=datetime.datetime(2012, 9, 1)
        )
        self.assertAggregatesEqual(aggregates, [
            _dpa((2012, 9, 1), {
                'minimum': '4.343445',
                'maximum': '324255.12',
                'sum': '348235.8068918',
                'count': '4',
            }),
        ])
        aggregates = self.monthly_aggregates.get_data_points(
            parameter_id,
            start_date=datetime.datetime(2018, 1, 12),
            end_date=datetime.datetime(5000, 12, 8)
        )
        self.assertAggregatesEqual(aggregates, [])

class TestMeasurements(CassandraTestMixin, unittest.TestCase):

    def setUp(self):
        super(TestMeasurements, self).setUp()
        self.measurements = parameters.Measurements()

    def test_basic_operation(self):
        parameter_id = 1253353566
        self.assertSequenceEqual(
            self.measurements.get_data_points(parameter_id),
            []
        )
        data_points = list(_get_test_data_points())
        self.measurements.insert_data_points(
            parameter_id,
            # Shuffled to ensure database ordering.
            data_points[500:] + data_points[:500]
        )
        self.assertSequenceEqual(
            self.measurements.get_data_points(parameter_id + 1),
            []
        )
        self.assertSequenceEqual(
            self.measurements.get_data_points(parameter_id),
            list(reversed(data_points))
        )
        self.assertSequenceEqual(
            self.measurements.get_data_points(
                parameter_id,
                start_date=datetime.datetime(2012, 9, 26, 11, 18),
                end_date=datetime.datetime(2012, 9, 26, 11, 18, 34)
            ),
            (
                _dp((2012, 9, 26, 11, 18, 0, 379482), '-22.7874213891'),
                _dp((2012, 9, 26, 11, 18, 33, 835339), '-10.5035473919'),
            )
        )
        self.assertSequenceEqual(
            self.measurements.get_data_points(
                parameter_id,
                start_date=datetime.datetime(2015, 9, 26, 11, 19),
                end_date=datetime.datetime(2050, 9, 26, 11, 19, 27)
            ),
            []
        )
        self.assertSequenceEqual(
            self.measurements.get_data_points(
                parameter_id,
                start_date=datetime.datetime(2015, 9, 26, 11, 19),
                end_date=datetime.datetime(2050, 9, 26, 11, 19, 27)
            ),
            []
        )
