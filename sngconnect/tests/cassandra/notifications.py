import unittest

from sngconnect.cassandra import notifications

from sngconnect.tests.cassandra import CassandraTestMixin

class TestNotifications(CassandraTestMixin, unittest.TestCase):

    def setUp(self):
        super(TestNotifications, self).setUp()
        self.notifications = notifications.Notifications()

    def test_basic_operation(self):
        user_id = 12532
        self.assertSequenceEqual(self.notifications.get_unread(user_id), [])
        self.notifications.set_unread([user_id], 13)
        self.notifications.set_unread([user_id], 15)
        self.notifications.set_unread([user_id], 187654)
        self.assertSequenceEqual(
            self.notifications.get_unread(user_id),
            [13, 15, 187654]
        )
        self.assertSequenceEqual(self.notifications.get_unread(user_id + 1), [])
        self.notifications.set_read(user_id, [87])
        self.assertSequenceEqual(
            self.notifications.get_unread(user_id),
            [13, 15, 187654]
        )
        self.notifications.set_read(user_id, [15])
        self.assertSequenceEqual(
            self.notifications.get_unread(user_id),
            [13, 187654]
        )
        self.notifications.set_read(user_id, [13, 187654])
        self.assertSequenceEqual(self.notifications.get_unread(user_id), [])
