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
    value_requested_at = colander.SchemaNode(
        colander.DateTime(),
        name='at'
    )
    requested_value = colander.SchemaNode(
        colander.Decimal(),
        name='current_value'
    )

class DataStreams(colander.SequenceSchema):
    data_stream = DataStream()

class GetChangedDataStreamsResponse(colander.MappingSchema):
    data_streams = DataStreams(name='datastreams')
