import unittest
import datetime

import pytz
import transaction
from pyramid import testing
from pyramid import httpexceptions

from sngconnect.api import views
from sngconnect.database import DBSession, System, Parameter, AlarmDefinition
from sngconnect.cassandra.parameters import Measurements
from sngconnect.cassandra.alarms import Alarms

from sngconnect.tests.api import ApiTestMixin

def _utc_datetime(*datetime_tuple):
    return pytz.utc.localize(datetime.datetime(*datetime_tuple))

class TestSystemParameterPut(ApiTestMixin, unittest.TestCase):

    def setUp(self):
        super(TestSystemParameterPut, self).setUp()
        system = System(
            id=1,
            name=u"System 1",
            description=u"Description",
            latitude=20.5,
            longitude=15.3,
            created=pytz.utc.localize(datetime.datetime.utcnow())
        )
        parameter = Parameter(
            id=1,
            name=u"Parameter 1",
            description=u"Description",
            measurement_unit=u"cm",
            system=system,
            writable=False
        )
        alarm_definition_1 = AlarmDefinition(
            id=1,
            alarm_type='MINIMAL_VALUE',
            boundary=-5,
            parameter=parameter
        )
        alarm_definition_2 = AlarmDefinition(
            id=2,
            alarm_type='MAXIMAL_VALUE',
            boundary=1000,
            parameter=parameter
        )
        DBSession.add_all([
            system,
            parameter,
            alarm_definition_1,
            alarm_definition_2,
        ])
        transaction.commit()

    def get_request(self, system_id, parameter_id, json_body='',
            content_type='application/json'):
        request = testing.DummyRequest()
        request.content_type = content_type
        request.matchdict.update({
            'system_id': system_id,
            'parameter_id': parameter_id,
        })
        request.json_body = json_body
        return request

    def test_invalid_ids(self):
        request = self.get_request(123, 435)
        self.assertRaises(
            httpexceptions.HTTPNotFound,
            views.system_parameter,
            request
        )

    def test_invalid_data_structure(self):
        request = self.get_request(1, 1, json_body={'foobar':[]})
        self.assertRaises(
            httpexceptions.HTTPBadRequest,
            views.system_parameter,
            request
        )

    def test_normal_operation(self):
        request = self.get_request(1, 1, json_body={
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
        response = views.system_parameter(request)
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

    def test_alarms(self):
        request = self.get_request(1, 1, json_body={
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
        response = views.system_parameter(request)
        self.assertEqual(response.status_code, 200)
        active_alarms = Alarms().get_active_alarms(1, 1)
        self.assertDictEqual(active_alarms, {
            1: _utc_datetime(2012, 9, 26, 18, 14, 35, 425000)
        })
        request = self.get_request(1, 1, json_body={
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
        response = views.system_parameter(request)
        self.assertEqual(response.status_code, 200)
        active_alarms = Alarms().get_active_alarms(1, 1)
        self.assertDictEqual(active_alarms, {
            1: _utc_datetime(2012, 9, 26, 18, 14, 35, 425000)
        })
        request = self.get_request(1, 1, json_body={
            'datapoints': [
                {
                    'at': '2012-09-27T18:14:35.425Z',
                    'value': '121344441344.24525',
                },
            ]
        })
        response = views.system_parameter(request)
        self.assertEqual(response.status_code, 200)
        active_alarms = Alarms().get_active_alarms(1, 1)
        self.assertDictEqual(active_alarms, {
            2: _utc_datetime(2012, 9, 27, 18, 14, 35, 425000)
        })
        request = self.get_request(1, 1, json_body={
            'datapoints': [
                {
                    'at': '2012-09-27T18:15:35.425Z',
                    'value': '234.2',
                },
            ]
        })
        response = views.system_parameter(request)
        self.assertEqual(response.status_code, 200)
        active_alarms = Alarms().get_active_alarms(1, 1)
        self.assertDictEqual(active_alarms, {})
