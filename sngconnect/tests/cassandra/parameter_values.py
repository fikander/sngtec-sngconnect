import unittest
import datetime
import decimal

from sngconnect.cassandra.parameter_values import (MeasurementDays,
    HourlyAverages, ParameterValues)

from sngconnect.tests.cassandra import CassandraTestMixin

def _dp(datetime_tuple, decimal_string):
    return (
        datetime.datetime(*datetime_tuple),
        decimal.Decimal(decimal_string)
    )

class TestMeasurementDays(CassandraTestMixin, unittest.TestCase):

    def setUp(self):
        super(TestMeasurementDays, self).setUp()
        self.measurement_days = MeasurementDays()

    def test_basic_operation(self):
        self.assertSequenceEqual(self.measurement_days.get_days(12), [])
        dates = [
            datetime.datetime(2012, 9, 11, 15, 18, 54),
            datetime.datetime(2012, 9, 15, 22,  0, 07),
            datetime.datetime(2012, 9, 18,  9, 12,  0),
            datetime.datetime(2012, 9, 19,  0,  0,  0),
        ]
        self.measurement_days.add_days(12, dates)
        self.assertSequenceEqual(self.measurement_days.get_days(12), [
            datetime.date(2012, 9, 11),
            datetime.date(2012, 9, 15),
            datetime.date(2012, 9, 18),
            datetime.date(2012, 9, 19),
        ])
        self.assertSequenceEqual(self.measurement_days.get_days(2452455), [])
        self.measurement_days.add_days(12, [
            datetime.datetime(2012, 9, 15, 22,  0, 07),
            datetime.datetime(2012, 7, 20, 23, 59, 59),
            datetime.datetime(2012, 9, 18,  8,  9, 17),
            datetime.datetime(2012, 7, 20, 23, 59, 59),
        ])
        self.assertSequenceEqual(self.measurement_days.get_days(12), [
            datetime.date(2012, 7, 20),
            datetime.date(2012, 9, 11),
            datetime.date(2012, 9, 15),
            datetime.date(2012, 9, 18),
            datetime.date(2012, 9, 19),
        ])
        self.assertSequenceEqual(self.measurement_days.get_days(1), [])

class TestHourlyAverages(CassandraTestMixin, unittest.TestCase):

    def setUp(self):
        super(TestHourlyAverages, self).setUp()
        self.parameter_values = ParameterValues()
        self.hourly_averages = HourlyAverages()

    def test_basic_operation(self):
        parameter_id = 23555
        data_points = [
            _dp((2012,  9, 21, 23, 59, 59, 999999), '522.343445'),
            _dp((2012,  9, 22, 15, 11, 12,      0), '4.343445'),
            _dp((2012,  9, 22,  9, 15,  5,   8001), '23454.0000018'),
            _dp((2012,  9, 22, 15, 43, 12, 300144), '324255.12'),
        ]
        self.parameter_values.insert_data_points(parameter_id, data_points)
        self.hourly_averages.recalculate_averages(parameter_id, [
            date for date, value in data_points
        ])
        averages = self.hourly_averages.get_averages(
            parameter_id,
            datetime.date(2012, 9, 22)
        )
        self.assertSequenceEqual(averages, [
            _dp((2012, 9, 22,  9), '23454.0000018'),
            _dp((2012, 9, 22, 15), '162129.7317225'),
        ])

class TestParameterValues(CassandraTestMixin, unittest.TestCase):

    def setUp(self):
        super(TestParameterValues, self).setUp()
        self.parameter_values = ParameterValues()

    def test_basic_operation(self):
        parameter_id = 1253353566
        stored_data_points = self.parameter_values.get_data_points(
            parameter_id,
        )
        self.assertSequenceEqual(stored_data_points, [])
        data_points = [
            _dp((2012,  9, 23, 15, 11, 12,      0), '2345554.3445'),
            _dp((2089, 12, 14, 11,  5,  5,   8001), '-2.2455555221'),
            _dp((2012,  9,  1, 15, 11, 12,      0), '4.343445'),
            _dp((2012,  1, 22, 15, 43, 12, 300144), '324255.12'),
            _dp((2012,  9, 22,  9, 15,  5,   8001), '23454.0000000001'),
        ]
        sorted_data_points = sorted(data_points, key=lambda x: x[0])
        self.parameter_values.insert_data_points(parameter_id, data_points)
        stored_data_points = self.parameter_values.get_data_points(
            parameter_id,
        )
        self.assertSequenceEqual(stored_data_points, sorted_data_points)
        self.parameter_values.insert_data_points(parameter_id, data_points)
        # And now the idempotency.
        stored_data_points = self.parameter_values.get_data_points(
            parameter_id,
        )
        self.assertSequenceEqual(stored_data_points, sorted_data_points)
