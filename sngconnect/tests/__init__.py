import logging
import decimal

from pyramid import testing

from sngconnect import configure_application
from sngconnect import cassandra as cassandra_management
from sngconnect.database import DBSession, ModelBase

class TestMixin(object):

    def setUp(self):
        logging.basicConfig(
            format='%(levelname)s: %(message)s',
            level=logging.WARNING
        )
        self.settings = {
            'database.url': 'sqlite://',
            'cassandra.servers': 'localhost:9160',
            'cassandra.keyspace': '__sngconnect_testing',
            'mail.sender': 'test@example.com',
            'session.secret': 'somesecret',
            'sngconnect.default_timezone': 'Europe/Warsaw',
            'sngconnect.device_image_upload_path': '',
            'sngconnect.appearance_assets_upload_path': '',
            'sngconnect.appearance_stylesheet_filename': '',
        }
        self.config = testing.setUp()
        cassandra_management.initialize_keyspace(self.settings)
        self.config = configure_application(
            self.settings,
            self.config
        )
        ModelBase.metadata.create_all(self.config.registry['database_engine'])

    def tearDown(self):
        DBSession.remove()
        cassandra_management.drop_keyspace(self.settings)
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
