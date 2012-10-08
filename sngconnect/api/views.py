import colander
from pyramid.view import view_config
from pyramid import httpexceptions
from pyramid.response import Response

from sngconnect.database import DBSession, System, Parameter
from sngconnect.cassandra.parameters import (Measurements, HourlyAggregates,
    DailyAggregates, MonthlyAggregates, LastDataPoints)
from sngconnect.api import schemas

@view_config(
    route_name='sngconnect.api.system_parameter',
    request_method='PUT'
)
def system_parameter(request):
    try:
        system_id = int(request.matchdict['system_id'])
        parameter_id = int(request.matchdict['parameter_id'])
    except (KeyError, ValueError):
        raise httpexceptions.HTTPNotFound("Invalid request arguments.")
    parameter_count = DBSession.query(Parameter).filter(
        System.id == system_id,
        Parameter.id == parameter_id
    ).count()
    if parameter_count == 0:
        raise httpexceptions.HTTPNotFound("Parameter not found.")
    if request.content_type != 'application/json':
        raise httpexceptions.HTTPBadRequest("Unsupported content type.")
    try:
        request_cstruct = request.json_body
    except ValueError as error:
        raise httpexceptions.HTTPBadRequest(
            "Error while decoding the request: %s" % str(error)
        )
    schema = schemas.PutDataPointsRequest()
    try:
        request_appstruct = schema.deserialize(request_cstruct)
    except colander.Invalid as error:
        raise httpexceptions.HTTPBadRequest('\r\n'.join((
            "Invalid data structure:",
            '\r\n'.join((
                '%s: %s' % (node_name, message)
                for node_name, message in error.asdict().iteritems()
            ))
        )))
    data_points = [
        (point['at'], point['value'])
        for point in request_appstruct['datapoints']
    ]
    Measurements().insert_data_points(parameter_id, data_points)
    # FIXME This is not wise for production use due to race condition concerns.
    dates = map(lambda x: x[0], data_points)
    HourlyAggregates().recalculate_aggregates(parameter_id, dates)
    DailyAggregates().recalculate_aggregates(parameter_id, dates)
    MonthlyAggregates().recalculate_aggregates(parameter_id, dates)
    LastDataPoints().update(system_id, parameter_id)
    # end of FIXME
    return Response()
