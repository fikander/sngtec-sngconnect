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
