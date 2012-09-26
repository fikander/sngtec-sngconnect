# -*- coding: utf-8 -*-

import unittest
import datetime

from sngconnect.cassandra import log

from sngconnect.tests.cassandra import CassandraTestMixin

def _dp(datetime_tuple, message):
    return (datetime.datetime(*datetime_tuple), message)

class TestLogs(CassandraTestMixin, unittest.TestCase):

    def setUp(self):
        super(TestLogs, self).setUp()
        self.logs = log.Logs()

    def test_basic_operation(self):
        log_id = 'somenamespace:1:5632'
        self.assertSequenceEqual(
            self.logs.get_log_entries(log_id),
            []
        )
        self.logs.insert_log_entries(
            log_id,
            (
                _dp((2012, 9, 26, 14, 12, 56, 234433), u"This is a message."),
                _dp((2012, 9, 24,  9,  0, 17,   2344), u"Zażółć gęślą jaźń!"),
                _dp((2012, 9, 26, 11, 17,  0,      8), u"대중적 음식의 하나."),
            )
        )
        self.assertSequenceEqual(
            self.logs.get_log_entries(log_id),
            (
                _dp((2012, 9, 24,  9,  0, 17,   2344), u"Zażółć gęślą jaźń!"),
                _dp((2012, 9, 26, 11, 17,  0,      8), u"대중적 음식의 하나."),
                _dp((2012, 9, 26, 14, 12, 56, 234433), u"This is a message."),
            )
        )
        self.assertSequenceEqual(
            self.logs.get_log_entries(log_id + ':13141341'),
            []
        )
        self.assertSequenceEqual(
            self.logs.get_log_entries(
                log_id,
                start_date=datetime.datetime(2012, 9, 26)
            ),
            (
                _dp((2012, 9, 26, 11, 17,  0,      8), u"대중적 음식의 하나."),
                _dp((2012, 9, 26, 14, 12, 56, 234433), u"This is a message."),
            )
        )
        self.assertSequenceEqual(
            self.logs.get_log_entries(
                log_id,
                start_date=datetime.datetime(2012, 9, 26),
                end_date=datetime.datetime(2012, 9, 26, 12)
            ),
            (
                _dp((2012, 9, 26, 11, 17,  0,      8), u"대중적 음식의 하나."),
            )
        )
