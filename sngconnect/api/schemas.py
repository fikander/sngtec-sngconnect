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
