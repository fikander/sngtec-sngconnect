import unittest
import datetime
import decimal

from sngconnect.cassandra import parameters

from sngconnect.tests.cassandra import CassandraTestMixin

def _dp(datetime_tuple, decimal_string):
    """Takes care of data point types."""
    return (
        datetime.datetime(*datetime_tuple),
        decimal.Decimal(decimal_string)
    )

def _dpa(datetime_tuple, aggregate_mapping):
    """Takes care of data point aggregate types."""
    return (
        datetime.datetime(*datetime_tuple),
        {
            key: decimal.Decimal(value)
            for key, value in aggregate_mapping.iteritems()
        }
    )

class TestMeasurementDays(CassandraTestMixin, unittest.TestCase):

    def setUp(self):
        super(TestMeasurementDays, self).setUp()
        self.measurement_days = parameters.MeasurementDays()

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

class TestHourlyAggregates(CassandraTestMixin, unittest.TestCase):

    def setUp(self):
        super(TestHourlyAggregates, self).setUp()
        self.measurements = parameters.Measurements()
        self.hourly_aggregates = parameters.HourlyAggregates()

    def test_basic_operation(self):
        parameter_id = 23555
        data_points = [
            _dp((2012,  9, 21, 23, 59, 59, 999999), '522.343445'),
            _dp((2012,  9, 22, 15, 11, 12,      0), '4.343445'),
            _dp((2012,  9, 22,  9, 15,  5,   8001), '23454.0000018'),
            _dp((2012,  9, 22, 15, 43, 12, 300144), '324255.12'),
        ]
        self.measurements.insert_data_points(parameter_id, data_points)
        self.hourly_aggregates.recalculate_aggregates(parameter_id, [
            date for date, value in data_points
        ])
        aggregates = self.hourly_aggregates.get_data_points(
            parameter_id,
            start_date=datetime.datetime(2012, 9, 22)
        )
        self.assertSequenceEqual(aggregates, [
            _dpa((2012, 9, 22,  9), {
                'minimum': '23454.0000018',
                'maximum': '23454.0000018',
                'average': '23454.0000018',
            }),
            _dpa((2012, 9, 22, 15), {
                'minimum': '4.343445',
                'maximum': '324255.12',
                'average': '162129.7317225',
            }),
        ])
        aggregates = self.hourly_aggregates.get_data_points(
            parameter_id,
            start_date=datetime.datetime(1998, 1, 12),
            end_date=datetime.datetime(5000, 12, 8)
        )
        self.assertSequenceEqual(aggregates, [
            _dpa((2012, 9, 21, 23), {
                'minimum': '522.343445',
                'maximum': '522.343445',
                'average': '522.343445',
            }),
            _dpa((2012, 9, 22,  9), {
                'minimum': '23454.0000018',
                'maximum': '23454.0000018',
                'average': '23454.0000018',
            }),
            _dpa((2012, 9, 22, 15), {
                'minimum': '4.343445',
                'maximum': '324255.12',
                'average': '162129.7317225',
            }),
        ])

class TestDailyAggregates(CassandraTestMixin, unittest.TestCase):

    def setUp(self):
        super(TestDailyAggregates, self).setUp()
        self.measurements = parameters.Measurements()
        self.daily_aggregates = parameters.DailyAggregates()

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
        self.daily_aggregates.recalculate_aggregates(parameter_id, changed_dates)
        aggregates = self.daily_aggregates.get_data_points(
            parameter_id,
            start_date=datetime.datetime(2012, 9, 22)
        )
        self.assertSequenceEqual(aggregates, [
            _dpa((2012, 9, 22), {
                'minimum': '4.343445',
                'maximum': '324255.12',
                'average': '115904.4878156',
            }),
        ])
        aggregates = self.daily_aggregates.get_data_points(
            parameter_id,
            start_date=datetime.datetime(2018, 1, 12),
            end_date=datetime.datetime(5000, 12, 8)
        )
        self.assertSequenceEqual(aggregates, [])

class TestMonthlyAggregates(CassandraTestMixin, unittest.TestCase):

    def setUp(self):
        super(TestMonthlyAggregates, self).setUp()
        self.measurements = parameters.Measurements()
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
        self.monthly_aggregates.recalculate_aggregates(parameter_id, changed_dates)
        aggregates = self.monthly_aggregates.get_data_points(
            parameter_id,
            start_date=datetime.datetime(2012, 9, 1)
        )
        self.assertSequenceEqual(aggregates, [
            _dpa((2012, 9, 1), {
                'minimum': '4.343445',
                'maximum': '324255.12',
                'average': '87058.95172295',
            }),
        ])
        aggregates = self.monthly_aggregates.get_data_points(
            parameter_id,
            start_date=datetime.datetime(2018, 1, 12),
            end_date=datetime.datetime(5000, 12, 8)
        )
        self.assertSequenceEqual(aggregates, [])

class TestYearlyAggregates(CassandraTestMixin, unittest.TestCase):

    def setUp(self):
        super(TestYearlyAggregates, self).setUp()
        self.measurements = parameters.Measurements()
        self.yearly_aggregates = parameters.YearlyAggregates()

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
        self.yearly_aggregates.recalculate_aggregates(parameter_id, changed_dates)
        aggregates = self.yearly_aggregates.get_data_points(
            parameter_id,
            start_date=datetime.datetime(2012, 1, 1)
        )
        self.assertSequenceEqual(aggregates, [
            _dpa((2012, 1, 1), {
                'minimum': '4.343445',
                'maximum': '324255.12',
                'average': '115904.4878156',
            }),
        ])
        aggregates = self.yearly_aggregates.get_data_points(
            parameter_id,
            start_date=datetime.datetime(2011, 1, 12),
            end_date=datetime.datetime(2011, 12, 8)
        )
        self.assertSequenceEqual(aggregates, [
            _dpa((2011, 1, 1), {
                'minimum': '522.343445',
                'maximum': '522.343445',
                'average': '522.343445',
            }),
        ])

class TestMeasurements(CassandraTestMixin, unittest.TestCase):

    def setUp(self):
        super(TestMeasurements, self).setUp()
        self.measurements = parameters.Measurements()

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
