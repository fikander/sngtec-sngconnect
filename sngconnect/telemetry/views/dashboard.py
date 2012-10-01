# -*- coding: utf-8 -*-

from pyramid.view import view_config

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
