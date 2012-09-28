import unittest
import datetime

import pytz
import transaction
from pyramid import testing
from pyramid import httpexceptions

from sngconnect.api import views
from sngconnect.database import DBSession, System, Parameter
from sngconnect.cassandra.parameters import Measurements

from sngconnect.tests.api import ApiTestMixin

class TestSystemParameterPut(ApiTestMixin, unittest.TestCase):

    def setUp(self):
        super(TestSystemParameterPut, self).setUp()
        system = System(
            id=1,
            name=u"System 1"
        )
        parameter = Parameter(
            id=1,
            name=u"Parameter 1",
            measurement_unit=u"cm",
            system=system,
            writable=False
        )
        DBSession.add_all([system, parameter])
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
                    'at': '2012-09-26T18:14:35.425Z',
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
                    datetime.datetime(
                        2012, 9, 26, 18, 14, 34, 345123,
                        tzinfo=pytz.utc
                    ),
                    '234254234.2344'
                ),
                (
                    datetime.datetime(
                        2012, 9, 26, 18, 14, 35, 425000,
                        tzinfo=pytz.utc
                    ),
                    '-234234444.24525'
                ),
            )
        )
