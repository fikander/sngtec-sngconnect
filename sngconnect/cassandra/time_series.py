import pytz
import numpy
import pycassa
from pycassa import types as pycassa_types

from sngconnect.cassandra.types import RealType, MicrosecondTimestampType
from sngconnect.cassandra.column_family_proxy import ColumnFamilyProxy

class TimeSeriesDateIndex(ColumnFamilyProxy):

    @classmethod
    def create(cls, system_manager, keyspace, **additional_kwargs):
        additional_kwargs.setdefault(
            'comparator_type',
            pycassa_types.DateType()
        )
        additional_kwargs.setdefault(
            'default_validation_class',
            pycassa_types.BytesType()
        )
        additional_kwargs.setdefault(
            'key_validation_class',
            pycassa_types.IntegerType(),
        )
        super(TimeSeriesDateIndex, cls).create(
            system_manager,
            keyspace,
            **additional_kwargs
        )

    def add_days(self, timeline_id, dates):
        values = dict(set((
            (self.force_precision(date), '') for date in dates
        )))
        self.column_family.insert(timeline_id, values)

    def get_days(self, timeline_id, start_date=None, end_date=None):
        kwargs = {}
        if start_date is not None:
            kwargs['column_start'] = self.force_precision(start_date)
        if end_date is not None:
            kwargs['column_finish'] = self.force_precision(end_date)
        try:
            return map(
                pytz.utc.localize,
                self.column_family.get(timeline_id, **kwargs).keys()
            )
        except pycassa.NotFoundException:
            return []

    def force_precision(self, date):
        if date.tzinfo is None:
            raise ValueError("Naive datetimes are not supported.")
        return pytz.utc.normalize(date.astimezone(pytz.utc)).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )

class TimeSeries(ColumnFamilyProxy):

    _date_index_class = None

    def __init__(self):
        super(TimeSeries, self).__init__()
        self.column_family.column_name_class = MicrosecondTimestampType()
        self.column_family.default_validation_class = RealType()

    @classmethod
    def create(cls, system_manager, keyspace, **additional_kwargs):
        additional_kwargs.setdefault(
            'comparator_type',
            pycassa_types.IntegerType()
        )
        additional_kwargs.setdefault(
            'default_validation_class',
            pycassa_types.AsciiType()
        )
        additional_kwargs.setdefault(
            'key_validation_class',
            pycassa_types.CompositeType(
                pycassa_types.IntegerType(),
                pycassa_types.DateType()
            ),
        )
        super(TimeSeries, cls).create(
            system_manager,
            keyspace,
            **additional_kwargs
        )

    def get_data_points(self, timeline_id, start_date=None, end_date=None):
        kwargs = {
            # Setting column count to Cassandra's maximum. We assume that
            # clients of this API know what they're doing.
            'column_count': 2000000000,
        }
        if start_date is not None:
            kwargs['column_start'] = start_date
            start_day = start_date.replace(
                hour=0,
                minute=0,
                second=0,
                microsecond=0
            )
        else:
            start_day = None
        if end_date is not None:
            kwargs['column_finish'] = end_date
            end_day = end_date.replace(
                hour=0,
                minute=0,
                second=0,
                microsecond=0
            )
        else:
            end_day = None
        if start_day is not None and start_day == end_day:
            try:
                return self.column_family.get(
                    self.get_row_key(timeline_id, start_date),
                    **kwargs
                ).items()
            except pycassa.NotFoundException:
                return []
        else:
            measurement_days = self._date_index_class()
            days = measurement_days.get_days(
                timeline_id,
                start_date=start_date,
                end_date=end_date
            )
            keys = [self.get_row_key(timeline_id, day) for day in days]
            result = self.column_family.multiget(keys, **kwargs)
            return sum((columns.items() for columns in result.values()), [])

    def aggregate(self, timeline_id, start_date=None, end_date=None):
        kwargs = {
            # Setting column count to Cassandra's maximum. We assume that
            # clients of this API know what they're doing.
            'column_count': 2000000000,
        }
        if start_date is not None:
            kwargs['column_start'] = start_date
        if end_date is not None:
            kwargs['column_finish'] = end_date
        measurement_days = self._date_index_class()
        dates = measurement_days.get_days(
            timeline_id,
            start_date=start_date,
            end_date=end_date
        )
        keys = set((self.get_row_key(timeline_id, date) for date in dates))
        values_sum = numpy.float128(0);
        values_minimum = None
        values_maximum = None
        values_count = 0
        for key in keys:
            try:
                values = numpy.array(
                    self.column_family.get(key, **kwargs).values(),
                    dtype=numpy.float128
                )
            except pycassa.NotFoundException:
                continue
            local_minimum = numpy.amin(values)
            local_maximum = numpy.amax(values)
            values_sum += numpy.sum(values)
            values_count += len(values)
            if values_minimum is None:
                values_minimum = local_minimum
            else:
                values_minimum = min(values_minimum, local_minimum)
            if values_maximum is None:
                values_maximum = local_maximum
            else:
                values_maximum = max(values_maximum, local_maximum)
        result = {
            'sum': str(values_sum),
            'count': str(values_count),
        }
        if values_maximum is not None:
            result['maximum'] = str(values_maximum)
        if values_minimum is not None:
            result['minimum'] = str(values_minimum)
        return result

    def get_row_key(self, timeline_id, date):
        return (timeline_id, date.replace(tzinfo=None))
