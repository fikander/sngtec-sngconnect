# -*- coding: utf-8 -*-

import datetime

import pytz
from sqlalchemy.orm import exc as database_exceptions
from pyramid.view import view_config
from pyramid import httpexceptions

from sngconnect.database import DBSession, System

@view_config(
    route_name='sngconnect.telemetry.dashboard',
    request_method='GET',
    renderer='sngconnect.telemetry:templates/dashboard.jinja2'
)
def dashboard(request):
    systems = DBSession.query(System).order_by(System.name)
    return {
        'systems_with_alarm_active': 2, # FIXME
        'systems': [
            {
                'id': system.id,
                'name': system.name,
                'dashboard_url': request.route_url(
                    'sngconnect.telemetry.system_dashboard',
                    system_id=system.id
                ),
                # FIXME
                'alarm_count': 5,
                'system': u"water pump",
                'owner': u"Some owner",
            }
            for system in systems
        ],
    }

@view_config(
    route_name='sngconnect.telemetry.system_dashboard',
    request_method='GET',
    renderer='sngconnect.telemetry:templates/system_dashboard.jinja2'
)
def system_dashboard(request):
    try:
        system = DBSession.query(System).filter(
            System.id == request.matchdict['system_id']
        ).one()
    except database_exceptions.NoResultFound:
        raise httpexceptions.HTTPNotFound()
    return {
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
            'dashboard_url': request.route_url(
                'sngconnect.telemetry.system_dashboard',
                system_id=system.id
            ),
        }
    }
