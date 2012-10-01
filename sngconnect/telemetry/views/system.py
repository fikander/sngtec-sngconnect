# -*- coding: utf-8 -*-

import datetime

import pytz
from sqlalchemy.orm import exc as database_exceptions
from pyramid.view import view_config
from pyramid import httpexceptions

from sngconnect.database import DBSession, System, Parameter

@view_config(
    route_name='sngconnect.telemetry.systems',
    request_method='GET'
)
def systems(request):
    raise httpexceptions.HTTPSeeOther(
        request.route_url('sngconnect.telemetry.dashboard')
    )

class SystemViewBase(object):

    def __init__(self, request):
        try:
            system = DBSession.query(System).filter(
                System.id == request.matchdict['system_id']
            ).one()
        except database_exceptions.NoResultFound:
            raise httpexceptions.HTTPNotFound()
        self.request = request
        self.system = system
        self.context = {
            # FIXME
            'active_alarms': [
                {
                    'activation_date': pytz.timezone('Europe/Warsaw').localize(
                        datetime.datetime(2012, 12, 1, 15, 16, 45)
                    ),
                    'parameter': u"nazwa parametru",
                    'type': u"temperatura kotła",
                    'description': u"jakiś niewielki błąd",
                },
                {
                    'activation_date': pytz.timezone('Europe/Warsaw').localize(
                        datetime.datetime(2012, 12, 1, 9, 21, 4)
                    ),
                    'parameter': u"temperatura wyjścia B",
                    'type': u"wartość minimalna przekroczona",
                    'description': u"jakiś straszliwy błąd",
                },
            ],
            'system': {
                'id': system.id,
                'name': system.name,
                'latitude': system.latitude,
                'longitude': system.longitude,
                'dashboard_url': request.route_url(
                    'sngconnect.telemetry.system_dashboard',
                    system_id=system.id
                ),
                'charts_url': request.route_url(
                    'sngconnect.telemetry.system_charts',
                    system_id=system.id
                ),
                'parameters_url': request.route_url(
                    'sngconnect.telemetry.system_parameters',
                    system_id=system.id
                ),
                'settings_url': request.route_url(
                    'sngconnect.telemetry.system_settings',
                    system_id=system.id
                ),
                'history_url': request.route_url(
                    'sngconnect.telemetry.system_history',
                    system_id=system.id
                ),
            }
        }

    def __call__(self):
        return self.context

@view_config(
    route_name='sngconnect.telemetry.system_dashboard',
    request_method='GET',
    renderer='sngconnect.telemetry:templates/system/dashboard.jinja2'
)
class SystemDashboard(SystemViewBase):
    pass

@view_config(
    route_name='sngconnect.telemetry.system_charts',
    request_method='GET',
    renderer='sngconnect.telemetry:templates/system/charts.jinja2'
)
class SystemCharts(SystemViewBase):
    pass

@view_config(
    route_name='sngconnect.telemetry.system_parameters',
    request_method='GET',
    renderer='sngconnect.telemetry:templates/system/parameters.jinja2'
)
class SystemParameters(SystemViewBase):
    def __call__(self):
        parameters = DBSession.query(Parameter).filter(
            System.id == self.system.id
        ).order_by(
            Parameter.name
        )
        self.context.update({
            'parameters': [
                {
                    'id': parameter.id,
                    'name': parameter.name,
                    'measurement_unit': parameter.measurement_unit,
                    'url': self.request.route_url(
                        'sngconnect.telemetry.system_parameter',
                        system_id=self.system.id,
                        parameter_id=parameter.id
                    ),
                }
                for parameter in parameters
            ]
        })
        return self.context

@view_config(
    route_name='sngconnect.telemetry.system_parameter',
    request_method='GET',
    renderer='sngconnect.telemetry:templates/system/parameter.jinja2'
)
class SystemParameter(SystemViewBase):
    def __call__(self):
        try:
            parameter = DBSession.query(Parameter).filter(
                System.id == self.system.id,
                Parameter.id == self.request.matchdict['parameter_id']
            ).one()
        except database_exceptions.NoResultFound:
            raise httpexceptions.HTTPNotFound()
        self.context.update({
            'parameter': parameter,
        })
        return self.context

@view_config(
    route_name='sngconnect.telemetry.system_settings',
    request_method='GET',
    renderer='sngconnect.telemetry:templates/system/settings.jinja2'
)
class SystemSettings(SystemViewBase):
    pass

@view_config(
    route_name='sngconnect.telemetry.system_setting',
    request_method='GET',
    renderer='sngconnect.telemetry:templates/system/setting.jinja2'
)
class SystemSetting(SystemViewBase):
    pass

@view_config(
    route_name='sngconnect.telemetry.system_history',
    request_method='GET',
    renderer='sngconnect.telemetry:templates/system/history.jinja2'
)
class SystemHistory(SystemViewBase):
    pass
