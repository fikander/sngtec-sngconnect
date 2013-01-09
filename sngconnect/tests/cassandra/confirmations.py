import unittest

from sngconnect.cassandra import confirmations

from sngconnect.tests.cassandra import CassandraTestMixin

class TestConfirmations(CassandraTestMixin, unittest.TestCase):

    def setUp(self):
        super(TestConfirmations, self).setUp()
        self.confirmations = confirmations.Confirmations()

    def test_basic_operation(self):
        user_id = 12532
        self.assertSequenceEqual(self.confirmations.get_unconfirmed(user_id), [])
        self.confirmations.set_unconfirmed([user_id], 13)
        self.confirmations.set_unconfirmed([user_id], 15)
        self.confirmations.set_unconfirmed([user_id], 187654)
        self.assertSequenceEqual(
            self.confirmations.get_unconfirmed(user_id),
            [13, 15, 187654]
        )
        self.assertSequenceEqual(self.confirmations.get_unconfirmed(user_id + 1), [])
        self.confirmations.set_confirmed(user_id, [87])
        self.assertSequenceEqual(
            self.confirmations.get_unconfirmed(user_id),
            [13, 15, 187654]
        )
        self.confirmations.set_confirmed(user_id, [15])
        self.assertSequenceEqual(
            self.confirmations.get_unconfirmed(user_id),
            [13, 187654]
        )
        self.confirmations.set_confirmed(user_id, [13, 187654])
        self.assertSequenceEqual(self.confirmations.get_unconfirmed(user_id), [])
