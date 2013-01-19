import colander

class DataPoint(colander.MappingSchema):
    date = colander.SchemaNode(
        colander.DateTime(),
        name='at'
    )
    value = colander.SchemaNode(
        colander.Decimal(),
        name='value'
    )

class DataPoints(colander.SequenceSchema):
    data_point = DataPoint()

class PutDataPointsRequest(colander.MappingSchema):
    data_points = DataPoints(name='datapoints')

class DataStream(colander.MappingSchema):

    id = colander.SchemaNode(
        colander.Integer()
    )
    label = colander.SchemaNode(
        colander.String(),
        name='label'
    )
    value_requested_at = colander.SchemaNode(
        colander.DateTime(),
        name='value_requested_at'
    )
    requested_value = colander.SchemaNode(
        colander.Decimal(),
        name='requested_value'
    )

class DataStreams(colander.SequenceSchema):
    data_stream = DataStream()

class GetChangedDataStreamsResponse(colander.MappingSchema):
    data_streams = DataStreams(name='datastreams')

class PostEventRequest(colander.MappingSchema):
    id = colander.SchemaNode(
        colander.Integer()
    )
    event_type = colander.SchemaNode(
        colander.String(),
        name='type',
        validator=colander.OneOf((
            'information',
            'system_warning',
            'system_error',
        ))
    )
    date = colander.SchemaNode(
        colander.DateTime(),
        name='timestamp'
    )
    message = colander.SchemaNode(
        colander.String()
    )

class Command(colander.MappingSchema):

    command = colander.SchemaNode(
        colander.String()
    )
    arguments = colander.SchemaNode(
        colander.Mapping(unknown='preserve')
    )

class Commands(colander.SequenceSchema):
    command = Command()

class GetCommandsResponse(colander.MappingSchema):
    commands = Commands()

class FeedModbusConfiguration(colander.MappingSchema):
    bandwidth = colander.SchemaNode(
        colander.Integer()
    )
    port = colander.SchemaNode(
        colander.String()
    )
    parity = colander.SchemaNode(
        colander.String(),
        validator=colander.OneOf([
            'even',
            'odd',
        ])
    )
    data_bits = colander.SchemaNode(
        colander.Integer()
    )
    stop_bits = colander.SchemaNode(
        colander.Integer()
    )
    timeout = colander.SchemaNode(
        colander.Integer()
    )
    endianness = colander.SchemaNode(
        colander.String(),
        validator=colander.OneOf([
            'big',
            'little',
        ])
    )
    polling_interval = colander.SchemaNode(
        colander.Integer()
    )

class DataStreamModbusConfiguration(colander.MappingSchema):
    register_type = colander.SchemaNode(
        colander.String(),
        validator=colander.OneOf([
            'holding',
            'input',
        ])
    )
    slave = colander.SchemaNode(
        colander.Integer()
    )
    address = colander.SchemaNode(
        colander.Integer()
    )
    count = colander.SchemaNode(
        colander.Integer()
    )

class DataStreamConfiguration(colander.MappingSchema):
    label = colander.SchemaNode(
        colander.String()
    )
    modbus = DataStreamModbusConfiguration()

class DataStreamConfigurations(colander.SequenceSchema):
    data_stream = DataStreamConfiguration()

class FeedConfiguration(colander.MappingSchema):
    id = colander.SchemaNode(
        colander.Integer()
    )
    modbus = FeedModbusConfiguration()
    data_streams = DataStreamConfigurations()

class FeedConfigurationResponse(colander.MappingSchema):
    feed = FeedConfiguration()

class ActivateResponse(colander.MappingSchema):
    api_key = colander.SchemaNode(
        colander.String()
    )
