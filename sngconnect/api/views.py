import json

import colander
from sqlalchemy.orm import exc as database_exceptions
from pyramid.view import view_config
from pyramid import httpexceptions
from pyramid.response import Response

from sngconnect.database import (DBSession, Feed, DataStreamTemplate,
    DataStream, AlarmDefinition, LogRequest, Message, Command)
from sngconnect.cassandra.data_streams import (Measurements, HourlyAggregates,
    DailyAggregates, MonthlyAggregates, LastDataPoints)
from sngconnect.cassandra.alarms import Alarms
from sngconnect.api import schemas

@view_config(
    route_name='sngconnect.api.feed_data_stream',
    request_method='PUT'
)
def feed_data_stream(request):
    """
    Upload datapoints
    Parameters:
        feed_id
        data_stream_label
    """
    try:
        feed_id = int(request.matchdict['feed_id'])
        data_stream_label = str(request.matchdict['data_stream_label'])
    except (KeyError, ValueError):
        raise httpexceptions.HTTPNotFound("Invalid request arguments.")
    try:
        data_stream = DBSession.query(DataStream).join(
            DataStreamTemplate
        ).filter(
            Feed.id == feed_id,
            DataStreamTemplate.label == data_stream_label
        ).one()
    except database_exceptions.NoResultFound:
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

    Measurements().insert_data_points(data_stream.id, data_points)

    # FIXME This is not wise for production use due to race condition concerns.
    dates = map(lambda x: x[0], data_points)
    HourlyAggregates().recalculate_aggregates(data_stream.id, dates)
    DailyAggregates().recalculate_aggregates(data_stream.id, dates)
    MonthlyAggregates().recalculate_aggregates(data_stream.id, dates)

    LastDataPoints().update(feed_id, data_stream.id)

    #
    # Turn alarms associated with datastreams on/off
    #
    alarm_definitions = DBSession.query(AlarmDefinition).filter(
        AlarmDefinition.data_stream_id == data_stream.id
    )
    last_date, last_value = LastDataPoints().get_last_data_stream_data_point(
        feed_id,
        data_stream.id
    )
    alarms_on = []
    alarms_off = []
    for alarm_definition in alarm_definitions:
        if alarm_definition.check_value(last_value) is None:
            alarms_off.append(alarm_definition.id)
        else:
            alarms_on.append(alarm_definition.id)
    Alarms().set_alarms_on(feed_id, data_stream.id, alarms_on, last_date)
    Alarms().set_alarms_off(feed_id, data_stream.id, alarms_off)

    #
    # Reset datastream's 'requested_value'  if any of the provided
    # values confirm request (assume small delta to cater for floating point precision errors?)
    # or for some reason requested value was never set (timeout)
    #
    if data_stream.requested_value is not None:

        for data_point in data_points:
            if data_point[1] == data_stream.requested_value:

                # tinyputer responded correctly with chnge that we requested
                data_stream.requested_value = None
                break

#        if data_stream.requested_value is not None:
#            # timeout after 5 minutes - reset data_stream.requested_value
#            td = datetime.datetime.now() - data_stream.value_requested_at 
#
#            if (td.total_seconds() > 300):
#                # TODO: create warning HistoryItem - we failed to set value on tinyputer 
#                data_stream.requested_value = None

        if data_stream.requested_value is None:
            DBSession.add(data_stream)

    # end of FIXME

    return Response()


@view_config(
    route_name='sngconnect.api.feed',
    request_method='GET'
)
def feed(request):
    """
    Get information about all data streams that have pending requested values
    Parameters:
        feed_id
    """

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
                'label': "FIXME: put template.label here", # FIXME: should be  'template.label'
                'requested_value': data_stream.requested_value,
                'value_requested_at': data_stream.value_requested_at,
            }
            for data_stream in data_streams
        ]
    })

    return Response(
        json.dumps(cstruct),
        content_type='application/json'
    )


@view_config(
    route_name='sngconnect.api.upload_log',
    request_method='POST'
)
def upload_log(request):
    """
    Store new piece of log sent by tinyputer. Logs can be sent as a response to 'upload_log' command
    which created placeholder LogRequest objects.
    
    Parameters:
        log_request_id
        log_request_hash
    """
    try:
        log_request_id = int(request.matchdict['log_request_id'])
        log_request_hash = str(request.matchdict['log_request_hash'])
    except (KeyError, ValueError):
        raise httpexceptions.HTTPNotFound("Invalid request arguments.")

    try:
        log_request = DBSession.query(LogRequest).filter(
            LogRequest.id == log_request_id,
            LogRequest.hash == log_request_hash,
            LogRequest.log == None
        ).one()

    except database_exceptions.NoResultFound:
        raise httpexceptions.HTTPNotFound("Log request not found.")

    log_request.log = request.body
    DBSession.add(log_request)

    return Response()


@view_config(
    route_name='sngconnect.api.events',
    request_method='POST'
)
def events(request):
    """
    Act on events coming FROM the device
    """
    try:
        feed_id = int(request.matchdict['feed_id'])
    except (KeyError, ValueError):
        raise httpexceptions.HTTPNotFound("Invalid request arguments.")
    try:
        feed = DBSession.query(Feed).filter(
            Feed.id == feed_id
        ).one()
    except database_exceptions.NoResultFound:
        raise httpexceptions.HTTPNotFound("Feed not found.")
    if request.content_type != 'application/json':
        raise httpexceptions.HTTPBadRequest("Unsupported content type.")
    try:
        request_cstruct = request.json_body
    except ValueError as error:
        raise httpexceptions.HTTPBadRequest(
            "Error while decoding the request: %s" % str(error)
        )

    schema = schemas.PostEventRequest()

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

    message_type_mapping = {
        'information': 'INFORMATION',
        'system_warning': 'WARNING',
        'system_error': 'ERROR',
    }
    message = Message(
        feed=feed,
        message_type=message_type_mapping[request_appstruct['type']],
        date=request_appstruct['timestamp'],
        content=request_appstruct['message']
    )
    DBSession.add(message)

    #
    # TODO: switch alarms associated with alarm_on, alarm_off events
    #

    return Response()


@view_config(
    route_name='sngconnect.api.commands',
    request_method='GET'
)
def commands(request):
    """
    Issue commands FOR the device
    """
    try:
        feed_id = int(request.matchdict['feed_id'])
    except (KeyError, ValueError):
        raise httpexceptions.HTTPNotFound("Invalid request arguments.")
    feed_count = DBSession.query(Feed).filter(
        Feed.id == feed_id
    ).count()
    if feed_count == 0:
        raise httpexceptions.HTTPNotFound("Feed not found.")

    commands = DBSession.query(
        Command.command,
        Command.arguments,
    ).filter(
        Command.feed_id == feed_id,
    )
    cstruct = schemas.GetCommandsResponse().serialize({
        'commands': [
            {
                'command': command.command,
                'arguments': command.arguments,
            }
            for command in commands
        ]
    })
    return Response(
        json.dumps(cstruct),
        content_type='application/json'
    )
