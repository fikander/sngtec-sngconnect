import unittest
import datetime
import decimal

from sngconnect.cassandra.parameters import *

from sngconnect.tests.cassandra import CassandraTestMixin

def _dp(datetime_tuple, decimal_string):
    """Takes care of data point types."""
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
        self.measurements = Measurements()
        self.hourly_averages = HourlyAverages()

    def test_basic_operation(self):
        parameter_id = 23555
        data_points = [
            _dp((2012,  9, 21, 23, 59, 59, 999999), '522.343445'),
            _dp((2012,  9, 22, 15, 11, 12,      0), '4.343445'),
            _dp((2012,  9, 22,  9, 15,  5,   8001), '23454.0000018'),
            _dp((2012,  9, 22, 15, 43, 12, 300144), '324255.12'),
        ]
        self.measurements.insert_data_points(parameter_id, data_points)
        self.hourly_averages.recalculate_averages(parameter_id, [
            date for date, value in data_points
        ])
        averages = self.hourly_averages.get_data_points(
            parameter_id,
            start_date=datetime.datetime(2012, 9, 22)
        )
        self.assertSequenceEqual(averages, [
            _dp((2012, 9, 22,  9), '23454.0000018'),
            _dp((2012, 9, 22, 15), '162129.7317225'),
        ])
        averages = self.hourly_averages.get_data_points(
            parameter_id,
            start_date=datetime.datetime(1998, 1, 12),
            end_date=datetime.datetime(5000, 12, 8)
        )
        self.assertSequenceEqual(averages, [
            _dp((2012, 9, 21, 23), '522.343445'),
            _dp((2012, 9, 22,  9), '23454.0000018'),
            _dp((2012, 9, 22, 15), '162129.7317225'),
        ])

class TestDailyAverages(CassandraTestMixin, unittest.TestCase):

    def setUp(self):
        super(TestDailyAverages, self).setUp()
        self.measurements = Measurements()
        self.daily_averages = DailyAverages()

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
        self.daily_averages.recalculate_averages(parameter_id, changed_dates)
        averages = self.daily_averages.get_data_points(
            parameter_id,
            start_date=datetime.datetime(2012, 9, 22)
        )
        self.assertSequenceEqual(averages, [
            _dp((2012, 9, 22), '115904.4878156'),
        ])
        averages = self.daily_averages.get_data_points(
            parameter_id,
            start_date=datetime.datetime(2018, 1, 12),
            end_date=datetime.datetime(5000, 12, 8)
        )
        self.assertSequenceEqual(averages, [])

class TestMonthlyAverages(CassandraTestMixin, unittest.TestCase):

    def setUp(self):
        super(TestMonthlyAverages, self).setUp()
        self.measurements = Measurements()
        self.monthly_averages = MonthlyAverages()

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
        self.monthly_averages.recalculate_averages(parameter_id, changed_dates)
        averages = self.monthly_averages.get_data_points(
            parameter_id,
            start_date=datetime.datetime(2012, 9, 1)
        )
        self.assertSequenceEqual(averages, [
            _dp((2012, 9, 1), '87058.95172295'),
        ])
        averages = self.monthly_averages.get_data_points(
            parameter_id,
            start_date=datetime.datetime(2018, 1, 12),
            end_date=datetime.datetime(5000, 12, 8)
        )
        self.assertSequenceEqual(averages, [])

class TestYearlyAverages(CassandraTestMixin, unittest.TestCase):

    def setUp(self):
        super(TestYearlyAverages, self).setUp()
        self.measurements = Measurements()
        self.yearly_averages = YearlyAverages()

    def test_basic_operation(self):
        parameter_id = 23555
        data_points = [
            _dp((2011,  9, 21, 23, 59, 59, 999999), '522.343445'),
            _dp((2012,  9, 22, 15, 11, 12,      0), '4.343445'),
            _dp((2012,  8, 22,  9, 15,  5,   8001), '23454.0000018'),
            _dp((2012,  1, 22, 15, 43, 12, 300144), '324255.12'),
        ]
        self.measurements.insert_data_points(parameter_id, data_points)
        changed_dates = [date for date, value in data_points]
        self.yearly_averages.recalculate_averages(parameter_id, changed_dates)
        averages = self.yearly_averages.get_data_points(
            parameter_id,
            start_date=datetime.datetime(2012, 1, 1)
        )
        self.assertSequenceEqual(averages, [
            _dp((2012, 1, 1), '115904.4878156'),
        ])
        averages = self.yearly_averages.get_data_points(
            parameter_id,
            start_date=datetime.datetime(2011, 1, 12),
            end_date=datetime.datetime(2011, 12, 8)
        )
        self.assertSequenceEqual(averages, [
            _dp((2011, 1, 1), '522.343445'),
        ])

class TestMeasurements(CassandraTestMixin, unittest.TestCase):

    def setUp(self):
        super(TestMeasurements, self).setUp()
        self.measurements = Measurements()

    def test_basic_operation(self):
        parameter_id = 1253353566
        stored_data_points = self.measurements.get_data_points(
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
        self.measurements.insert_data_points(parameter_id, data_points)
        stored_data_points = self.measurements.get_data_points(
            parameter_id,
        )
        self.assertSequenceEqual(stored_data_points, sorted_data_points)
        self.measurements.insert_data_points(parameter_id, data_points)
        # And now the idempotency.
        stored_data_points = self.measurements.get_data_points(
            parameter_id,
        )
        self.assertSequenceEqual(stored_data_points, sorted_data_points)
