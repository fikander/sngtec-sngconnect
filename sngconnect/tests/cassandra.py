import unittest
import datetime
import decimal
import logging

from pyramid import testing

from sngconnect.cassandra import (
    initialize_keyspace,
    drop_keyspace,
    initialize_connection_pool,
    ParameterValues
)

class CassandraTestMixin(object):

    def setUp(self):
        logging.basicConfig(
            format='%(levelname)s: %(message)s',
            level=logging.INFO
        )
        self.config = testing.setUp()
        self.testing_cassandra_configuration = {
            'cassandra.servers': 'localhost:9160',
            'cassandra.keyspace': '__sngconnect_testing'
        }
        initialize_keyspace(self.testing_cassandra_configuration)
        initialize_connection_pool(self.testing_cassandra_configuration)

    def tearDown(self):
        testing.tearDown()
        drop_keyspace(self.testing_cassandra_configuration)

class TestParameterValues(CassandraTestMixin, unittest.TestCase):

    def setUp(self):
        super(TestParameterValues, self).setUp()
        self.parameter_values = ParameterValues()

    def test_inserting_data_points(self):
        self.parameter_values.insert_data_points(
            12,
            (
                (
                    datetime.datetime(2012, 9, 22, 15, 11, 12, 0),
                    decimal.Decimal('2345554.3445')
                ),
                (
                    datetime.datetime(2012, 9, 22, 15, 43, 12, 300),
                    decimal.Decimal('324255.12')
                ),
                (
                    datetime.datetime(2012, 9, 22, 9, 15, 5, 8),
                    decimal.Decimal('2345555')
                ),
            )
        )
