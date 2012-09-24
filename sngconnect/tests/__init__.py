import logging
import decimal

from pyramid import testing

class TestMixin(object):

    def setUp(self):
        logging.basicConfig(
            format='%(levelname)s: %(message)s',
            level=logging.WARNING
        )
        self.config = testing.setUp()

    def tearDown(self):
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
