# -*- coding: utf-8 -*-

import datetime
import decimal

import pytz
from sqlalchemy.orm import exc as database_exceptions
from pyramid.view import view_config
from pyramid import httpexceptions

from sngconnect.database import DBSession, System, Parameter
from sngconnect.cassandra import parameters as parameters_store

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
                'description': system.description,
                'address': system.address,
                'latitude': system.latitude,
                'longitude': system.longitude,
                'created': system.created,
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
        last_data_points = (
            parameters_store.LastDataPoints().get_last_parameter_data_points(
                self.system.id
            )
        )
        parameters_serialized = []
        for parameter in parameters:
            daily_aggregates = (
                parameters_store.DailyAggregates().get_data_points(
                    parameter.id,
                    start_date=pytz.utc.localize(datetime.datetime.utcnow()),
                    end_date=pytz.utc.localize(datetime.datetime.utcnow())
                )
            )
            try:
                today = daily_aggregates[0][1]
            except IndexError:
                today = None
            data_point = last_data_points.get(parameter.id, None)
            if data_point is None:
                last_value = None
            else:
                last_value = {
                    'value': decimal.Decimal(data_point[1]),
                    'date': data_point[0],
                }
            parameters_serialized.append({
                'id': parameter.id,
                'name': parameter.name,
                'minimal_value': parameter.minimal_value,
                'maximal_value': parameter.maximal_value,
                'measurement_unit': parameter.measurement_unit,
                'url': self.request.route_url(
                    'sngconnect.telemetry.system_parameter',
                    system_id=self.system.id,
                    parameter_id=parameter.id
                ),
                'last_value': last_value,
                'today': today,
            })
        self.context.update({
            'parameters': parameters_serialized,
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
        hourly_aggregates = parameters_store.HourlyAggregates().get_data_points(
            parameter.id,
            start_date=pytz.utc.localize(datetime.datetime.utcnow()),
            end_date=pytz.utc.localize(datetime.datetime.utcnow())
        )
        try:
            this_hour = hourly_aggregates[0][1]
            this_hour['mean'] = (
                decimal.Decimal(this_hour['sum'])
                / decimal.Decimal(this_hour['count'])
            )
        except IndexError:
            this_hour = None
        daily_aggregates = parameters_store.DailyAggregates().get_data_points(
            parameter.id,
            start_date=pytz.utc.localize(datetime.datetime.utcnow()),
            end_date=pytz.utc.localize(datetime.datetime.utcnow())
        )
        try:
            today = daily_aggregates[0][1]
            today['mean'] = (
                decimal.Decimal(today['sum'])
                / decimal.Decimal(today['count'])
            )
        except IndexError:
            today = None
        monthly_aggregates = (
            parameters_store.MonthlyAggregates().get_data_points(
                parameter.id,
                start_date=pytz.utc.localize(datetime.datetime.utcnow()),
                end_date=pytz.utc.localize(datetime.datetime.utcnow())
            )
        )
        try:
            this_month = monthly_aggregates[0][1]
            this_month['mean'] = (
                decimal.Decimal(this_month['sum'])
                / decimal.Decimal(this_month['count'])
            )
        except IndexError:
            this_month = None
        last_data_point = (
            parameters_store.LastDataPoints().get_last_parameter_data_point(
                self.system.id,
                parameter.id
            )
        )
        self.context.update({
            'parameter': {
                'id': parameter.id,
                'name': parameter.name,
                'description': parameter.description,
                'last_value': {
                    'date': last_data_point[0],
                    'value': decimal.Decimal(last_data_point[1]),
                } if last_data_point else None,
                'this_hour': dict(map(
                    lambda x: (x[0], decimal.Decimal(x[1])),
                    this_hour.items()
                )) if this_hour is not None else None,
                'today': dict(map(
                    lambda x: (x[0], decimal.Decimal(x[1])),
                    today.items()
                )) if today is not None else None,
                'this_month': dict(map(
                    lambda x: (x[0], decimal.Decimal(x[1])),
                    this_month.items()
                )) if this_month is not None else None,
            },
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
