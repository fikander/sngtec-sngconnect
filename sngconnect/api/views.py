import json

import colander
from pyramid.view import view_config
from pyramid import httpexceptions
from pyramid.response import Response

from sngconnect.database import (DBSession, Feed, DataStreamTemplate,
    DataStream, AlarmDefinition)
from sngconnect.cassandra.data_streams import (Measurements, HourlyAggregates,
    DailyAggregates, MonthlyAggregates, LastDataPoints)
from sngconnect.cassandra.alarms import Alarms
from sngconnect.api import schemas

@view_config(
    route_name='sngconnect.api.feed_data_stream',
    request_method='PUT'
)
def feed_data_stream(request):
    try:
        feed_id = int(request.matchdict['feed_id'])
        data_stream_id = int(request.matchdict['data_stream_id'])
    except (KeyError, ValueError):
        raise httpexceptions.HTTPNotFound("Invalid request arguments.")
    data_stream_count = DBSession.query(DataStream).filter(
        Feed.id == feed_id,
        DataStream.id == data_stream_id
    ).count()
    if data_stream_count == 0:
        raise httpexceptions.HTTPNotFound("DataStream not found.")
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
    Measurements().insert_data_points(data_stream_id, data_points)
    # FIXME This is not wise for production use due to race condition concerns.
    dates = map(lambda x: x[0], data_points)
    HourlyAggregates().recalculate_aggregates(data_stream_id, dates)
    DailyAggregates().recalculate_aggregates(data_stream_id, dates)
    MonthlyAggregates().recalculate_aggregates(data_stream_id, dates)
    LastDataPoints().update(feed_id, data_stream_id)
    alarm_definitions = DBSession.query(AlarmDefinition).filter(
        AlarmDefinition.data_stream_id == data_stream_id
    )
    last_date, last_value = LastDataPoints().get_last_data_stream_data_point(
        feed_id,
        data_stream_id
    )
    alarms_on = []
    alarms_off = []
    for alarm_definition in alarm_definitions:
        if alarm_definition.check_value(last_value) is None:
            alarms_off.append(alarm_definition.id)
        else:
            alarms_on.append(alarm_definition.id)
    Alarms().set_alarms_on(feed_id, data_stream_id, alarms_on, last_date)
    Alarms().set_alarms_off(feed_id, data_stream_id, alarms_off)
    # end of FIXME
    return Response()

@view_config(
    route_name='sngconnect.api.feed',
    request_method='GET'
)
def feed(request):
    try:
        feed_id = int(request.matchdict['feed_id'])
    except (KeyError, ValueError):
        raise httpexceptions.HTTPNotFound("Invalid request arguments.")
    feed_count = DBSession.query(Feed).filter(
        Feed.id == feed_id
    ).count()
    if feed_count == 0:
        raise httpexceptions.HTTPNotFound("Feed not found.")
    data_streams = DBSession.query(
        DataStream.id,
        DataStream.requested_value,
        DataStream.value_requested_at
    ).join(DataStreamTemplate).filter(
        Feed.id == feed_id,
        DataStreamTemplate.writable == True,
        DataStream.requested_value != None,
        DataStream.value_requested_at != None
    )
    cstruct = schemas.GetChangedDataStreamsResponse().serialize({
        'datastreams': [
            {
                'id': data_stream.id,
                'current_value': data_stream.requested_value,
                'at': data_stream.value_requested_at,
            }
            for data_stream in data_streams
        ]
    })
    return Response(
        json.dumps(cstruct),
        content_type='application/json'
    )
