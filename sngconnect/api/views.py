import json
import sys
import uuid
import decimal
import hmac
import hashlib

import colander
import sqlalchemy as sql
from sqlalchemy.orm import exc as database_exceptions
from pyramid.view import view_config
from pyramid import httpexceptions
from pyramid.response import Response

from sngconnect.database import (DBSession, Feed, DataStreamTemplate,
    DataStream, AlarmDefinition, LogRequest, Message, Command)
from sngconnect.services.message import MessageService
from sngconnect.cassandra.data_streams import (Measurements, HourlyAggregates,
    DailyAggregates, MonthlyAggregates, LastDataPoints)
from sngconnect.cassandra.alarms import Alarms
from sngconnect.api import schemas

def authorize_request(request, feed_id):
    api_key = DBSession.query(Feed).filter(
        Feed.id == feed_id
    ).value('api_key')
    if api_key is None:
        raise httpexceptions.HTTPNotFound("Feed not found.")
    valid_signature = (
        hmac.new(
            api_key,
            ':'.join((request.path_qs, request.body)),
            hashlib.sha256
        ).hexdigest()
    )
    actual_signature = request.headers.get('Signature', None)
    if valid_signature != actual_signature:
        raise httpexceptions.HTTPUnauthorized("Invalid signature.")

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
    authorize_request(request, feed_id)
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
    # FIXME This may be not wise for production use due to race condition
    # concerns.
    dates = map(lambda x: x[0], data_points)
    HourlyAggregates().recalculate_aggregates(data_stream.id, dates)
    DailyAggregates().recalculate_aggregates(data_stream.id, dates)
    MonthlyAggregates().recalculate_aggregates(data_stream.id, dates)
    LastDataPoints().update(feed_id, data_stream.id)
    last_date, last_value = LastDataPoints().get_last_data_stream_data_point(
        feed_id,
        data_stream.id
    )
    last_value = decimal.Decimal(last_value)
    # Turn alarms associated with datastreams on/off
    alarm_definitions = DBSession.query(AlarmDefinition).filter(
        AlarmDefinition.data_stream_id == data_stream.id
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
    # Set requested value to None if applied.
    if data_stream.writable and data_stream.requested_value is not None:
        error = abs(data_stream.requested_value - last_value)
        maximal_error = (
            decimal.Decimal(str(sys.float_info.epsilon)) * max((
                2 ** -1022,
                abs(data_stream.requested_value),
                abs(last_value))
            )
        )
        if error <= maximal_error:
            DBSession.query(DataStream).filter(
                DataStream.id == data_stream.id
            ).update({
                'requested_value': None,
                'value_requested_at': None,
            })
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
    authorize_request(request, feed_id)
    if request.params.get('filter', None) != 'requested':
        raise httpexceptions.HTTPBadRequest("Unsupported filter parameter.")
    data_streams = DBSession.query(
        DataStream.id,
        DataStream.requested_value,
        DataStream.value_requested_at,
        DataStreamTemplate.label
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
                'label': data_stream.label,
                'requested_value': data_stream.requested_value,
                'value_requested_at': data_stream.value_requested_at
            }
            for data_stream in data_streams ]
        }
    )
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
    authorize_request(request, feed_id)
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
        feed_id=feed_id,
        message_type=message_type_mapping[request_appstruct['type']],
        date=request_appstruct['timestamp'],
        content=request_appstruct['message']
    )
    MessageService(request).create_message(message)
    # TODO: switch alarms associated with alarm_on, alarm_off events
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
    authorize_request(request, feed_id)
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

@view_config(
    route_name='sngconnect.api.activate',
    request_method='GET'
)
def activate(request):
    """
    Activate the feed and get configuration.
    """
    try:
        feed_id = int(request.matchdict['feed_id'])
        activation_code = request.POST['activation_code']
        device_uuid = uuid.UUID(request.POST['device_uuid'])
    except (KeyError, ValueError):
        raise httpexceptions.HTTPNotFound("Invalid request arguments.")
    try:
        feed = DBSession.query(Feed).filter(id=feed_id).one()
    except database_exceptions.NoResultFound:
        raise httpexceptions.HTTPNotFound("Feed not found.")
    if feed.activation_code == activation_code:
        if not feed.has_activation_code_expired():
            feed.activation_code = None
            feed.activation_code_regenerated = None
            feed.device_uuid = device_uuid.hex
            DBSession.add(feed)
            data_stream_templates = DBSession.query(
                DataStreamTemplate
            ).filter(
                DataStreamTemplate.feed_template == feed.template
            ).order_by(
                sql.asc(DataStreamTemplate.label)
            )
            cstruct = schemas.ActivateResponse().serialize({
                'feed': {
                    'id': feed.id,
                    'api_key': feed.api_key,
                    'modbus': {
                        'bandwidth': feed.modbus_bandwidth,
                        'port': feed.modbus_port,
                        'parity': (
                            'even' if feed.modbus_parity == 'EVEN' else 'odd'
                        ),
                        'data_bits': feed.modbus_data_bits,
                        'stop_bits': feed.modbus_stop_bits,
                        'timeout': feed.modbus_timeout,
                        'endianness': (
                            'big'
                            if feed.modbus_endianness == 'BIG' else
                            'little'
                        ),
                        'polling_interval': feed.modbus_polling_interval,
                    },
                    'data_streams': [
                        {
                            'label': data_stream_template.label,
                            'modbus': {
                                'register_type': (
                                    'holding'
                                    if data_stream_template.modbus_register_type == 'HOLDING' else
                                    'input'
                                ),
                                'slave': data_stream_template.modbus_slave,
                                'address': data_stream_template.modbus_address,
                                'count': data_stream_template.modbus_count,
                            },
                        }
                        for data_stream_template in data_stream_templates
                    ],
                },
            })
            return Response(
                json.dumps(cstruct),
                content_type='application/json'
            )
        else:
            raise httpexceptions.HTTPBadRequest(
                "This activation code has expired."
            )
    else:
        raise httpexceptions.HTTPForbidden("Invalid activation code.")
