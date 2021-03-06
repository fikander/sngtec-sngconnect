import unittest
import datetime
import hmac
import hashlib
import decimal
import json

import pytz
import transaction
from pyramid import testing
from pyramid import httpexceptions

from sngconnect.api import views
from sngconnect.database import (DBSession, FeedTemplate, Feed,
    DataStreamTemplate, DataStream, AlarmDefinition, LogRequest, Message,
    Command)
from sngconnect.cassandra.data_streams import Measurements
from sngconnect.cassandra.alarms import Alarms

from sngconnect.tests.api import ApiTestMixin

def _utc_datetime(*datetime_tuple):
    return pytz.utc.localize(datetime.datetime(*datetime_tuple))

def _sign(request, api_key):
    request.headers['Signature'] = (
        hmac.new(
            api_key,
            ':'.join((request.path_qs, request.body)),
            hashlib.sha256
        ).hexdigest()
    )

class TestFeedDataStreamPut(ApiTestMixin, unittest.TestCase):

    def setUp(self):
        super(TestFeedDataStreamPut, self).setUp()
        feed_template = FeedTemplate(
            id=1,
            name='Feed template 1',
            modbus_bandwidth=9600,
            modbus_port='/dev/ttyS0',
            modbus_parity='EVEN',
            modbus_data_bits=8,
            modbus_stop_bits=1,
            modbus_timeout=5,
            modbus_endianness='BIG',
            modbus_polling_interval=120,
            dashboard_layout='IMAGE',
        )
        feed = Feed(
            id=1,
            template=feed_template,
            name=u"Feed 1",
            description=u"Description",
            latitude=20.5,
            longitude=15.3,
            created=pytz.utc.localize(datetime.datetime.utcnow())
        )
        self.api_key = feed.api_key
        data_stream_template_1 = DataStreamTemplate(
            id=1,
            feed_template=feed_template,
            label='data_stream',
            name=u"DataStream 1",
            description=u"Description",
            measurement_unit=u"cm",
            writable=False,
            modbus_register_type='HOLDING',
            modbus_slave=1,
            modbus_address=1,
            modbus_count=1
        )
        data_stream_template_2 = DataStreamTemplate(
            id=2,
            feed_template=feed_template,
            label='data_stream_2',
            name=u"DataStream 2",
            description=u"Description",
            measurement_unit=u"cm",
            writable=True,
            modbus_register_type='HOLDING',
            modbus_slave=1,
            modbus_address=2,
            modbus_count=1
        )
        data_stream_1 = DataStream(
            id=1,
            template=data_stream_template_1,
            feed=feed,
        )
        data_stream_2 = DataStream(
            id=2,
            template=data_stream_template_2,
            feed=feed,
            requested_value=decimal.Decimal('1234'),
            value_requested_at=pytz.utc.localize(datetime.datetime.now())
        )
        alarm_definition_1 = AlarmDefinition(
            id=1,
            alarm_type='MINIMAL_VALUE',
            boundary=-5,
            data_stream=data_stream_1
        )
        alarm_definition_2 = AlarmDefinition(
            id=2,
            alarm_type='MAXIMAL_VALUE',
            boundary=1000,
            data_stream=data_stream_1
        )
        DBSession.add_all([
            feed_template,
            feed,
            data_stream_template_1,
            data_stream_template_2,
            data_stream_1,
            data_stream_2,
            alarm_definition_1,
            alarm_definition_2,
        ])
        #transaction.commit()

    def get_request(self, feed_id, data_stream_label, json_body='',
            content_type='application/json'):
        request = testing.DummyRequest()
        request.content_type = content_type
        request.matchdict.update({
            'feed_id': feed_id,
            'data_stream_label': data_stream_label,
        })
        request.json_body = json_body
        _sign(request, self.api_key)
        return request

    def test_invalid_ids(self):
        request = self.get_request(123, 'data_stream_fake')
        self.assertRaises(
            httpexceptions.HTTPNotFound,
            views.feed_data_stream,
            request
        )

    def test_invalid_data_structure(self):
        request = self.get_request(1, 'data_stream', json_body={'foobar': []})
        self.assertRaises(
            httpexceptions.HTTPBadRequest,
            views.feed_data_stream,
            request
        )

    def test_normal_operation(self):
        request = self.get_request(1, 'data_stream', json_body={
            'datapoints': [
                {
                    'at': '2012-09-26T18:14:34.345123Z',
                    'value': '234254234.2344',
                },
                {
                    'at': '2012-09-26T18:14:35.425-07:00',
                    'value': '-234234444.24525',
                },
            ]
        })
        response = views.feed_data_stream(request)
        self.assertEqual(response.status_code, 200)
        self.assertSequenceEqual(
            Measurements().get_data_points(1),
            (
                (
                    _utc_datetime(2012, 9, 26, 18, 14, 34, 345123),
                    '234254234.2344'
                ),
                (
                    _utc_datetime(2012, 9, 27, 1, 14, 35, 425000),
                    '-234234444.24525'
                ),
            )
        )

    def test_multiple_datastreams(self):
        request = self.get_request(1, None, json_body={
            'datastreams': [{
                'label': 'data_stream',
                'datapoints': [
                    {
                        'at': '2012-09-26T18:14:34.345123Z',
                        'value': '234254234.2344',
                    },
                    {
                        'at': '2012-09-26T18:14:35.425-07:00',
                        'value': '-234234444.24525',
                    },
                ]
            }, {
                'label': 'data_stream_2',
                'datapoints': [
                    {
                        'at': '2013-08-23T18:14:34.345123Z',
                        'value': '90.0',
                    },
                ]
            }
            ]
        })
        response = views.feed_put(request)
        self.assertEqual(response.status_code, 200)
        self.assertSequenceEqual(
            Measurements().get_data_points(1),
            (
                (
                    _utc_datetime(2012, 9, 26, 18, 14, 34, 345123),
                    '234254234.2344'
                ),
                (
                    _utc_datetime(2012, 9, 27, 1, 14, 35, 425000),
                    '-234234444.24525'
                ),
            )
        )
        self.assertSequenceEqual(
            Measurements().get_data_points(2),
            (
                (
                    _utc_datetime(2013, 8, 23, 18, 14, 34, 345123),
                    '90.0'
                ),
            )
        )

    def test_alarms(self):
        request = self.get_request(1, 'data_stream', json_body={
            'datapoints': [
                {
                    'at': '2012-09-26T18:14:34.345123Z',
                    'value': '134.2344',
                },
                {
                    'at': '2012-09-26T18:14:35.425Z',
                    'value': '-23.24525',
                },
            ]
        })
        response = views.feed_data_stream(request)
        self.assertEqual(response.status_code, 200)
        active_alarms = Alarms().get_active_alarms(1, 1)
        self.assertDictEqual(active_alarms, {
            1: _utc_datetime(2012, 9, 26, 18, 14, 35, 425000)
        })
        request = self.get_request(1, 'data_stream', json_body={
            'datapoints': [
                {
                    'at': '2012-09-25T18:14:34.345123Z',
                    'value': '245255.2344',
                },
                {
                    'at': '2012-09-25T18:14:35.425Z',
                    'value': '0.24525',
                },
            ]
        })
        response = views.feed_data_stream(request)
        self.assertEqual(response.status_code, 200)
        active_alarms = Alarms().get_active_alarms(1, 1)
        self.assertDictEqual(active_alarms, {
            1: _utc_datetime(2012, 9, 26, 18, 14, 35, 425000)
        })
        request = self.get_request(1, 'data_stream', json_body={
            'datapoints': [
                {
                    'at': '2012-09-27T18:14:35.425Z',
                    'value': '121344441344.24525',
                },
            ]
        })
        response = views.feed_data_stream(request)
        self.assertEqual(response.status_code, 200)
        active_alarms = Alarms().get_active_alarms(1, 1)
        self.assertDictEqual(active_alarms, {
            2: _utc_datetime(2012, 9, 27, 18, 14, 35, 425000)
        })
        request = self.get_request(1, 'data_stream', json_body={
            'datapoints': [
                {
                    'at': '2012-09-27T18:15:35.425Z',
                    'value': '234.2',
                },
            ]
        })
        response = views.feed_data_stream(request)
        self.assertEqual(response.status_code, 200)
        active_alarms = Alarms().get_active_alarms(1, 1)
        self.assertDictEqual(active_alarms, {})

    def test_reset_requested_value(self):
        # Request value in data stream.
        self.assertEqual(
            DBSession.query(DataStream).filter(
                DataStream.id == 2
            ).value('requested_value'),
            1234
        )
        # Pretend value has not yet been set by tinyputer - requested_value
        # still exists.
        request = self.get_request(1, 'data_stream_2', json_body={
            'datapoints': [
                {
                    'at': '2012-10-13T17:01:00.345123Z',
                    'value': '134.2344',
                },
                {
                    'at': '2012-10-13T17:02:00.425Z',
                    'value': '-23.24525',
                },
            ]
        })
        response = views.feed_data_stream(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            DBSession.query(DataStream).filter(
                DataStream.id == 2
            ).value('requested_value'),
            1234
        )
        # Pretend value has been set by tinyputer - requested_value reset.
        request = self.get_request(1, 'data_stream_2', json_body={
            'datapoints': [
                {
                    'at': '2012-10-13T17:02:30.345123Z',
                    'value': '1234',
                },
            ]
        })
        #with transaction.manager
        response = views.feed_data_stream(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            DBSession.query(DataStream).filter(
                DataStream.id == 2
            ).value('requested_value'),
            None
        )
        request = self.get_request(1, 'data_stream_2', json_body={
            'datapoints': [
                {
                    'at': '2012-10-13T17:03:30.345123Z',
                    'value': '4321',
                },
            ]
        })
        response = views.feed_data_stream(request)
        self.assertEqual(response.status_code, 200)


class TestFeedGet(ApiTestMixin, unittest.TestCase):

    def setUp(self):
        super(TestFeedGet, self).setUp()
        feed_template = FeedTemplate(
            id=1,
            name='Feed template 1',
            modbus_bandwidth=9600,
            modbus_port='/dev/ttyS0',
            modbus_parity='EVEN',
            modbus_data_bits=8,
            modbus_stop_bits=1,
            modbus_timeout=5,
            modbus_endianness='BIG',
            modbus_polling_interval=120,
            dashboard_layout='IMAGE',
        )
        feed = Feed(
            id=1,
            template=feed_template,
            name=u"Feed 1",
            description=u"Description",
            latitude=20.5,
            longitude=15.3,
            created=pytz.utc.localize(datetime.datetime.utcnow())
        )
        self.api_key = feed.api_key
        data_stream_template1 = DataStreamTemplate(
            id=1,
            feed_template=feed_template,
            label='data_stream_1',
            name=u"DataStream 1",
            description=u"Description",
            measurement_unit=u"cm",
            writable=False,
            modbus_register_type='HOLDING',
            modbus_slave=1,
            modbus_address=1,
            modbus_count=1
        )
        data_stream_template2 = DataStreamTemplate(
            id=2,
            feed_template=feed_template,
            label='data_stream_2',
            name=u"DataStream 2",
            description=u"Description",
            measurement_unit=u"mm",
            writable=True,
            modbus_register_type='HOLDING',
            modbus_slave=1,
            modbus_address=2,
            modbus_count=1
        )
        data_stream1 = DataStream(
            id=1,
            template=data_stream_template1,
            feed=feed,
        )
        data_stream2 = DataStream(
            id=2,
            template=data_stream_template2,
            feed=feed,
        )
        DBSession.add_all([
            feed_template,
            feed,
            data_stream_template1,
            data_stream_template2,
            data_stream1,
            data_stream2,
        ])
        #transaction.commit()

    def get_request(self, feed_id):
        request = testing.DummyRequest()
        request.matchdict.update({
            'feed_id': feed_id,
        })
        request.GET.update({'filter': 'requested'})
        _sign(request, self.api_key)
        return request

    def test_invalid_ids(self):
        request = self.get_request(123)
        self.assertRaises(
            httpexceptions.HTTPNotFound,
            views.feed,
            request
        )

    def test_normal_operation(self):
        request = self.get_request(1)
        response = views.feed(request)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            json.loads(response.body),
            {'datastreams': [],}
        )

        DBSession.query(DataStream).filter(DataStream.id == 2).update({
            'requested_value': decimal.Decimal('2345.5'),
            'value_requested_at': _utc_datetime(2012, 10, 9, 12, 34, 11),
        })
        #transaction.commit()
        request = self.get_request(1)
        response = views.feed(request)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            json.loads(response.body),
            {
                u'datastreams': [
                    {
                        u'id': u'2',
                        u'label': u'data_stream_2',
                        u'requested_value': u'2345.5000000000000000000000000',
                        u'value_requested_at': u'2012-10-09T12:34:11+00:00',
                    },
                ],
            }
        )

        DBSession.query(DataStream).filter(DataStream.id == 2).update({
            'requested_value': decimal.Decimal('-144.25'),
            'value_requested_at': _utc_datetime(2012, 10, 9, 12, 35, 11),
        })
        #transaction.commit()
        request = self.get_request(1)
        response = views.feed(request)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            json.loads(response.body),
            {
                u'datastreams': [
                    {
                        u'id': u'2',
                        u'label': u'data_stream_2',
                        u'requested_value': u'-144.2500000000000000000000000',
                        u'value_requested_at': u'2012-10-09T12:35:11+00:00',
                    },
                ],
            }
        )

class TestUploadLog(ApiTestMixin, unittest.TestCase):

    def setUp(self):
        super(TestUploadLog, self).setUp()
        feed_template = FeedTemplate(
            id=1,
            name='Feed template 1',
            modbus_bandwidth=9600,
            modbus_port='/dev/ttyS0',
            modbus_parity='EVEN',
            modbus_data_bits=8,
            modbus_stop_bits=1,
            modbus_timeout=5,
            modbus_endianness='BIG',
            modbus_polling_interval=120,
            dashboard_layout='IMAGE',
        )
        feed = Feed(
            id=1,
            template=feed_template,
            name=u"Feed 1",
            description=u"Description",
            latitude=20.5,
            longitude=15.3,
            created=pytz.utc.localize(datetime.datetime.utcnow())
        )
        self.api_key = feed.api_key
        log_request = LogRequest(
            id=1,
            feed=feed,
            period_start=_utc_datetime(2012, 1, 16),
            period_end=_utc_datetime(2012, 8, 1)
        )
        self.hash = log_request.hash
        DBSession.add_all([
            feed_template,
            feed,
            log_request,
        ])
        #transaction.commit()

    def get_request(self, log_request_id, log_request_hash, body=''):
        request = testing.DummyRequest()
        request.matchdict.update({
            'log_request_id': log_request_id,
            'log_request_hash': log_request_hash,
        })
        request.body = body
        return request

    def test_invalid_ids(self):
        request = self.get_request(234234, '234234')
        #with transaction.manager:
        self.assertRaises(
            httpexceptions.HTTPNotFound,
            views.upload_log,
            request
        )
        request = self.get_request(1, self.hash + '34')
        #with transaction.manager:
        self.assertRaises(
            httpexceptions.HTTPNotFound,
            views.upload_log,
            request
        )

    def test_empty_log(self):
        request = self.get_request(1, self.hash)
        #with transaction.manager:
        response = views.upload_log(request)
        self.assertEqual(response.status_code, 200)
        request = self.get_request(1, self.hash)
        #with transaction.manager:
        self.assertRaises(
            httpexceptions.HTTPNotFound,
            views.upload_log,
            request
        )
        log_request = (
            DBSession.query(LogRequest).filter(LogRequest.id == 1).one()
        )
        self.assertEqual(log_request.log, '')

    def test_normal_operation(self):
        request = self.get_request(1, self.hash, "SOME LOG")
        #with transaction.manager:
        response = views.upload_log(request)
        self.assertEqual(response.status_code, 200)
        log_request = (
            DBSession.query(LogRequest).filter(LogRequest.id == 1).one()
        )
        self.assertEqual(log_request.log, "SOME LOG")


class TestEvents(ApiTestMixin, unittest.TestCase):

    def setUp(self):
        super(TestEvents, self).setUp()
        feed_template = FeedTemplate(
            id=1,
            name='Feed template 1',
            modbus_bandwidth=9600,
            modbus_port='/dev/ttyS0',
            modbus_parity='EVEN',
            modbus_data_bits=8,
            modbus_stop_bits=1,
            modbus_timeout=5,
            modbus_endianness='BIG',
            modbus_polling_interval=120,
            dashboard_layout='IMAGE',
        )
        feed = Feed(
            id=1,
            template=feed_template,
            name=u"Feed 1",
            description=u"Description",
            latitude=20.5,
            longitude=15.3,
            created=pytz.utc.localize(datetime.datetime.utcnow())
        )
        self.api_key = feed.api_key
        DBSession.add_all([
            feed_template,
            feed,
        ])
        #transaction.commit()

    def get_request(self, feed_id, json_body='',
            content_type='application/json'):
        request = testing.DummyRequest()
        request.content_type = content_type
        request.matchdict.update({
            'feed_id': feed_id,
        })
        request.json_body = json_body
        _sign(request, self.api_key)
        return request

    def test_invalid_ids(self):
        request = self.get_request(234234)
        #with transaction.manager:
        self.assertRaises(
            httpexceptions.HTTPNotFound,
            views.events,
            request
        )

    def test_invalid_data_structure(self):
        request = self.get_request(1, json_body={'foobar': []})
        self.assertRaises(
            httpexceptions.HTTPBadRequest,
            views.events,
            request
        )

    def test_normal_operation(self):
        request = self.get_request(1, json_body={
            'id': '123',
            'type': 'information',
            'timestamp': '2012-05-26T12:23:23',
            'message': 'some message',
        })
        #with transaction.manager:
        response = views.events(request)
        self.assertEqual(response.status_code, 200)
        message = DBSession.query(Message).one()
        self.assertEqual(message.message_type, 'INFORMATION')
        date = message.date
        if date.tzinfo is None:
            date = pytz.utc.localize(date)
        self.assertEqual(date, _utc_datetime(2012, 5, 26, 12, 23, 23))
        self.assertEqual(message.content, 'some message')
        self.assertEqual(message.feed_id, 1)
        self.assertEqual(message.data_stream_id, None)

class TestCommands(ApiTestMixin, unittest.TestCase):

    def setUp(self):
        super(TestCommands, self).setUp()
        feed_template = FeedTemplate(
            id=1,
            name='Feed template 1',
            modbus_bandwidth=9600,
            modbus_port='/dev/ttyS0',
            modbus_parity='EVEN',
            modbus_data_bits=8,
            modbus_stop_bits=1,
            modbus_timeout=5,
            modbus_endianness='BIG',
            modbus_polling_interval=120,
            dashboard_layout='IMAGE',
        )
        feed = Feed(
            id=1,
            template=feed_template,
            name=u"Feed 1",
            description=u"Description",
            latitude=20.5,
            longitude=15.3,
            created=pytz.utc.localize(datetime.datetime.utcnow())
        )
        self.api_key = feed.api_key
        DBSession.add_all([
            feed_template,
            feed,
        ])
        #transaction.commit()

    def get_request(self, feed_id):
        request = testing.DummyRequest()
        request.matchdict.update({
            'feed_id': feed_id,
        })
        _sign(request, self.api_key)
        return request

    def test_invalid_ids(self):
        request = self.get_request(234234)
        #with transaction.manager:
        self.assertRaises(
            httpexceptions.HTTPNotFound,
            views.commands,
            request
        )

    def test_normal_operation(self):
        request = self.get_request(1)
        response = views.commands(request)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json_body, {
            'commands': [],
        })
        command = Command(
            feed_id=1,
            date=_utc_datetime(2012, 5, 17, 23, 4, 11),
            command='upload_log',
            arguments={
                'url': 'http://example.org',
            }
        )
        #with transaction.manager:
        DBSession.add(command)
        request = self.get_request(1)
        response = views.commands(request)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json_body, {
            u'commands': [
                {
                    u'command': u'upload_log',
                    u'arguments': {
                        u'url': u'http://example.org',
                    },
                },
            ],
        })

class TestFeedConfiguration(ApiTestMixin, unittest.TestCase):

    def setUp(self):
        super(TestFeedConfiguration, self).setUp()
        feed_template = FeedTemplate(
            id=1,
            name='Feed template 1',
            modbus_bandwidth=9600,
            modbus_port='/dev/ttyS0',
            modbus_parity='EVEN',
            modbus_data_bits=8,
            modbus_stop_bits=1,
            modbus_timeout=5,
            modbus_endianness='BIG',
            modbus_polling_interval=120,
            dashboard_layout='IMAGE',
        )
        feed = Feed(
            id=1,
            template=feed_template,
            name=u"Feed 1",
            description=u"Description",
            latitude=20.5,
            longitude=15.3,
            created=pytz.utc.localize(datetime.datetime.utcnow())
        )
        self.api_key = feed.api_key
        data_stream_template_1 = DataStreamTemplate(
            id=1,
            feed_template=feed_template,
            label='data_stream',
            name=u"DataStream 1",
            description=u"Description",
            measurement_unit=u"cm",
            writable=False,
            modbus_register_type='HOLDING',
            modbus_slave=1,
            modbus_address=1,
            modbus_count=1
        )
        data_stream_template_2 = DataStreamTemplate(
            id=2,
            feed_template=feed_template,
            label='data_stream_2',
            name=u"DataStream 2",
            description=u"Description",
            measurement_unit=u"cm",
            writable=True,
            modbus_register_type='HOLDING',
            modbus_slave=1,
            modbus_address=2,
            modbus_count=1
        )
        DBSession.add_all([
            feed_template,
            feed,
            data_stream_template_1,
            data_stream_template_2,
        ])
        #transaction.commit()

    def get_request(self, feed_id):
        request = testing.DummyRequest()
        request.matchdict.update({
            'feed_id': feed_id,
        })
        _sign(request, self.api_key)
        return request

    def test_invalid_ids(self):
        request = self.get_request(234234)
        #with transaction.manager:
        self.assertRaises(
            httpexceptions.HTTPNotFound,
            views.feed_configuration,
            request
        )

    def test_normal_operation(self):
        request = self.get_request(1)
        #with transaction.manager:
        response = views.feed_configuration(request)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json_body, {
            'feed': {
                'id': '1',
                'modbus': {
                    'bandwidth': '9600',
                    'port': '/dev/ttyS0',
                    'parity': 'even',
                    'data_bits': '8',
                    'stop_bits': '1',
                    'timeout': '5',
                    'endianness': 'big',
                    'polling_interval': '120',
                },
                'data_streams': [
                    {
                        'label': 'data_stream',
                        'modbus': {
                            'register_type': 'holding',
                            'slave': '1',
                            'address': '1',
                            'count': '1',
                        },
                    },
                    {
                        'label': 'data_stream_2',
                        'modbus': {
                            'register_type': 'holding',
                            'slave': '1',
                            'address': '2',
                            'count': '1',
                        },
                    },
                ],
            }
        })


class TestActivate(ApiTestMixin, unittest.TestCase):

    def setUp(self):
        super(TestActivate, self).setUp()
        feed_template = FeedTemplate(
            id=1,
            name='Feed template 1',
            modbus_bandwidth=9600,
            modbus_port='/dev/ttyS0',
            modbus_parity='EVEN',
            modbus_data_bits=8,
            modbus_stop_bits=1,
            modbus_timeout=5,
            modbus_endianness='BIG',
            modbus_polling_interval=120,
            dashboard_layout='IMAGE',
        )
        feed = Feed(
            id=1,
            template=feed_template,
            name=u"Feed 1",
            description=u"Description",
            latitude=20.5,
            longitude=15.3,
            created=pytz.utc.localize(datetime.datetime.utcnow()),
            api_key='some-api-key',
            activation_code='some-activation-code',
            activation_code_regenerated=pytz.utc.localize(
                datetime.datetime.utcnow()
            ),
        )
        self.activation_code = feed.activation_code
        DBSession.add_all([
            feed_template,
            feed,
        ])
        #transaction.commit()

    def get_request(self, feed_id, activation_code, device_uuid):
        request = testing.DummyRequest()
        request.matchdict.update({
            'feed_id': feed_id,
        })
        if activation_code is not None:
            request.POST['activation_code'] = activation_code
        if device_uuid is not None:
            request.POST['device_uuid'] = device_uuid
        return request

    def test_invalid_ids(self):
        request = self.get_request(234234, 'somecode', 'some-uuid')
        #with transaction.manager:
        self.assertRaises(
            httpexceptions.HTTPNotFound,
            views.activate,
            request
        )

    def test_invalid_code(self):
        request = self.get_request(
            1,
            self.activation_code + 'foobar',
            '2feefa53-8dc9-441e-8c81-b8aa7fb919fd'
        )
        #with transaction.manager:
        self.assertRaises(
            httpexceptions.HTTPForbidden,
            views.activate,
            request
        )

    def test_expired_code(self):
        #with transaction.manager:
        DBSession.query(Feed).filter(
            Feed.id == 1
        ).update({
            'activation_code_regenerated': (
                pytz.utc.localize(datetime.datetime.utcnow() - datetime.timedelta(days=300))
            )
        })
        request = self.get_request(
            1,
            self.activation_code,
            '2feefa53-8dc9-441e-8c81-b8aa7fb919fd'
        )
        #with transaction.manager:
        self.assertRaises(
            httpexceptions.HTTPForbidden,
            views.activate,
            request
        )

    def test_normal_operation(self):
        request = self.get_request(
            1,
            self.activation_code,
            '2feefa53-8dc9-441e-8c81-b8aa7fb919fd'
        )
        #with transaction.manager:
        response = views.activate(request)
        self.assertEqual(response.status_code, 200)
        self.assertSequenceEqual(response.json_body.keys(), ['api_key'])
        self.assertNotEqual(response.json_body['api_key'], 'some-api-key')
        feed = DBSession.query(Feed).filter(Feed.id == 1).one()
        self.assertEqual(feed.device_uuid, '2feefa538dc9441e8c81b8aa7fb919fd')
        self.assertEqual(feed.api_key, response.json_body['api_key'])
