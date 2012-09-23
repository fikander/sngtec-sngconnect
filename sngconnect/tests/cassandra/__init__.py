from sngconnect import cassandra
from sngconnect.cassandra import connection_pool
from sngconnect.tests import TestMixin

class CassandraTestMixin(TestMixin):

    def setUp(self):
        super(CassandraTestMixin, self).setUp()
        self.testing_cassandra_configuration = {
            'cassandra.servers': 'localhost:9160',
            'cassandra.keyspace': '__sngconnect_testing'
        }
        cassandra.initialize_keyspace(self.testing_cassandra_configuration)
        connection_pool.initialize_connection_pool(
            self.testing_cassandra_configuration
        )

    def tearDown(self):
        super(CassandraTestMixin, self).tearDown()
        cassandra.drop_keyspace(self.testing_cassandra_configuration)
