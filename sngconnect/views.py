import datetime

import numpy
from pyramid.view import view_config

from sngconnect.database import DBSession, System, Parameter
from sngconnect.cassandra.parameters import (HourlyAggregates, DailyAggregates,
    Measurements)

@view_config(
    route_name='dev.index',
    renderer='sngconnect:templates/index.jinja2'
)
def dev_index(request):
    systems = DBSession.query(System).all()
    return {
        'systems': systems,
    }

@view_config(
    route_name='dev.system',
    renderer='sngconnect:templates/system.jinja2'
)
def dev_system(request):
    system = DBSession.query(System).filter(
        System.id == request.matchdict['system_id']
    ).one()
    return {
        'system': system,
    }

@view_config(
    route_name='dev.parameter',
    renderer='sngconnect:templates/parameter.jinja2'
)
def dev_parameter(request):
    parameter = DBSession.query(Parameter).filter(
        Parameter.id == request.matchdict['parameter_id']
    ).one()
    last_hour = Measurements().get_data_points(
        parameter.id,
        start_date=(datetime.datetime.utcnow() - datetime.timedelta(hours=1))
    )
    last_day = Measurements().get_data_points(
        parameter.id,
        start_date=(datetime.datetime.utcnow() - datetime.timedelta(days=1))
    )
    last_week_data = HourlyAggregates().get_data_points(
        parameter.id,
        start_date=(datetime.datetime.utcnow() - datetime.timedelta(days=7))
    )
    last_week = []
    for date, data in last_week_data:
        data['error'] = max(
            numpy.float128(data['mean']) - numpy.float128(data['minimum']),
            numpy.float128(data['mean']) - numpy.float128(data['maximum'])
        ) / 4
        last_week.append((date, data))
    last_month_data = DailyAggregates().get_data_points(
        parameter.id,
        start_date=(datetime.datetime.utcnow() - datetime.timedelta(days=30))
    )
    last_month = []
    for date, data in last_month_data:
        data['error'] = max(
            numpy.float128(data['mean']) - numpy.float128(data['minimum']),
            numpy.float128(data['mean']) - numpy.float128(data['maximum'])
        ) / 4
        last_month.append((date, data))
    return {
        'parameter': parameter,
        'last_hour': last_hour,
        'last_day': last_day,
        'last_week': last_week,
        'last_month': last_month,
    }
