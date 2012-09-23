import unittest
import datetime
import decimal
import logging

from pyramid import testing

from sngconnect import cassandra
from sngconnect.cassandra import connection_pool
from sngconnect.cassandra.parameter_values import (ParameterValuesKeyIndex,
    ParameterValues)

class CassandraTestMixin(object):

    def setUp(self):
        logging.basicConfig(
            format='%(levelname)s: %(message)s',
            level=logging.WARNING
        )
        self.config = testing.setUp()
        self.testing_cassandra_configuration = {
            'cassandra.servers': 'localhost:9160',
            'cassandra.keyspace': '__sngconnect_testing'
        }
        cassandra.initialize_keyspace(self.testing_cassandra_configuration)
        connection_pool.initialize_connection_pool(
            self.testing_cassandra_configuration
        )

    def tearDown(self):
        testing.tearDown()
        cassandra.drop_keyspace(self.testing_cassandra_configuration)

class TestParameterValuesKeyIndex(CassandraTestMixin, unittest.TestCase):

    def setUp(self):
        super(TestParameterValuesKeyIndex, self).setUp()
        self.key_index = ParameterValuesKeyIndex()

    def test_basic_operation(self):
        self.assertSequenceEqual(self.key_index.get_dates(12), [])
        dates = [
            datetime.datetime(2012, 9, 11, 15, 18, 54),
            datetime.datetime(2012, 9, 15, 22,  0, 07),
            datetime.datetime(2012, 9, 18,  9, 12,  0),
            datetime.datetime(2012, 9, 19,  0,  0,  0),
        ]
        self.key_index.add_dates(12, dates)
        self.assertSequenceEqual(self.key_index.get_dates(12), [
            datetime.date(2012, 9, 11),
            datetime.date(2012, 9, 15),
            datetime.date(2012, 9, 18),
            datetime.date(2012, 9, 19),
        ])
        self.assertSequenceEqual(self.key_index.get_dates(2452455), [])
        self.key_index.add_dates(12, [
            datetime.datetime(2012, 9, 15, 22,  0, 07),
            datetime.datetime(2012, 7, 20, 23, 59, 59),
            datetime.datetime(2012, 9, 18,  8,  9, 17),
            datetime.datetime(2012, 7, 20, 23, 59, 59),
        ])
        self.assertSequenceEqual(self.key_index.get_dates(12), [
            datetime.date(2012, 7, 20),
            datetime.date(2012, 9, 11),
            datetime.date(2012, 9, 15),
            datetime.date(2012, 9, 18),
            datetime.date(2012, 9, 19),
        ])
        self.assertSequenceEqual(self.key_index.get_dates(1), [])

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
            self._dp((2012,  9, 23, 15, 11, 12,      0), '2345554.3445'),
            self._dp((2089, 12, 14, 11,  5,  5,   8001), '-2.2455555221'),
            self._dp((2012,  9,  1, 15, 11, 12,      0), '4.343445'),
            self._dp((2012,  1, 22, 15, 43, 12, 300144), '324255.12'),
            self._dp((2012,  9, 22,  9, 15,  5,   8001), '23454.0000000001'),
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

    def _dp(self, datetime_tuple, decimal_string):
        return (
            datetime.datetime(*datetime_tuple),
            decimal.Decimal(decimal_string)
        )
