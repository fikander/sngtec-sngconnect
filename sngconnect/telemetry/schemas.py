import colander

class DataPoint(colander.TupleSchema):
    date = colander.SchemaNode(
        colander.DateTime()
    )
    value = colander.SchemaNode(
        colander.Decimal()
    )

class DataPoints(colander.SequenceSchema):
    data_point = DataPoint()

class ChartDataResponse(colander.SequenceSchema):
    data_points = DataPoints()
