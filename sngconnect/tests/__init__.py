import logging
import decimal

import sqlalchemy
from pyramid import testing

from sngconnect import cassandra as cassandra_management
from sngconnect.cassandra import connection_pool
from sngconnect.database import DBSession, ModelBase

class TestMixin(object):

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
        cassandra_management.initialize_keyspace(
            self.testing_cassandra_configuration
        )
        connection_pool.initialize_connection_pool(
            self.testing_cassandra_configuration
        )
        database_engine = sqlalchemy.create_engine('sqlite://')
        DBSession.configure(bind=database_engine)
        ModelBase.metadata.create_all(database_engine)

    def tearDown(self):
        DBSession.remove()
        cassandra_management.drop_keyspace(self.testing_cassandra_configuration)
        testing.tearDown()

    def assertAggregatesEqual(self, first, second):
        self.assertEqual(len(first), len(second))
        self.assertSequenceEqual(
            [date for date, aggregates in first],
            [date for date, aggregates in second]
        )
        for i in range(len(first)):
            for key in first[i][1].iterkeys():
                self.assertIn(key, first[i][1])
                self.assertIn(key, second[i][1])
                self.assertAlmostEqual(
                    decimal.Decimal(first[i][1][key]),
                    decimal.Decimal(second[i][1][key]),
                    6
                )
