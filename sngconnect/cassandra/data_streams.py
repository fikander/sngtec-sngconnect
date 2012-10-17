import datetime
import calendar
import time

import pytz
import numpy
import pycassa
from pycassa import types as pycassa_types

from sngconnect.cassandra.column_family_proxy import ColumnFamilyProxy
from sngconnect.cassandra.time_series import TimeSeries, TimeSeriesDateIndex
from sngconnect.cassandra.types import RealType, MicrosecondTimestampType

class MeasurementDays(TimeSeriesDateIndex):

    _column_family_name = 'MeasurementDays'

class Measurements(TimeSeries):

    _column_family_name = 'Measurements'
    _date_index_class = MeasurementDays

    def insert_data_points(self, data_stream_id, data_points):
        rows = {}
        for measurement_datetime, value in data_points:
            key = self.get_row_key(data_stream_id, measurement_datetime)
            rows.setdefault(key, {})
            rows[key][measurement_datetime] = value
        self.column_family.batch_insert(rows)
        self._date_index_class().add_days(
            data_stream_id,
            (date for date, value in data_points)
        )

    def get_row_key(self, data_stream_id, date):
        if date.tzinfo is None:
            raise ValueError("Naive datetime is not supported.")
        date = pytz.utc.normalize(date.astimezone(pytz.utc)).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )
        return super(Measurements, self).get_row_key(data_stream_id, date)

class AggregatesStore(TimeSeries):

    _date_index_class = MeasurementDays

    def __init__(self):
        super(AggregatesStore, self).__init__()
        self.column_family.super_column_name_class = MicrosecondTimestampType()
        self.column_family.column_name_class = pycassa_types.AsciiType()

    @classmethod
    def create(cls, system_manager, keyspace, **additional_kwargs):
        additional_kwargs.setdefault(
            'super',
            True
        )
        additional_kwargs.setdefault(
            'subcomparator_type',
            pycassa_types.AsciiType()
        )
        super(AggregatesStore, cls).create(
            system_manager,
            keyspace,
            **additional_kwargs
        )

    def get_data_points(self, data_stream_id, start_date=None, end_date=None):
        if start_date is not None:
            start_date = self.force_precision(start_date)
        if end_date is not None:
            end_date = self.force_precision(end_date)
        return super(AggregatesStore, self).get_data_points(
            data_stream_id,
            start_date,
            end_date
        )

    def aggregate(self, data_stream_id, start_date=None, end_date=None):
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
            data_stream_id,
            start_date=start_date,
            end_date=end_date
        )
        keys = set((self.get_row_key(data_stream_id, date) for date in dates))
        values_sum = numpy.float128(0);
        values_count = numpy.float128(0)
        values_minimum = None
        values_maximum = None
        for key in keys:
            try:
                result = map(
                    lambda point: (
                        point['minimum'],
                        point['maximum'],
                        point['count'],
                        point['sum'],
                    ),
                    self.column_family.get(
                        key,
                        **kwargs
                    ).values()
                )
            except pycassa.NotFoundException:
                continue
            aggregates = numpy.array(
                result,
                dtype=numpy.float128
            )
            local_minimum = aggregates[:,0].min()
            local_maximum = aggregates[:,1].max()
            values_count += aggregates[:,2].sum()
            values_sum += aggregates[:,3].sum()
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
            'count': str(int(values_count)),
        }
        if values_maximum is not None:
            result['maximum'] = str(values_maximum)
        if values_minimum is not None:
            result['minimum'] = str(values_minimum)
        return result

    def recalculate_aggregates(self, data_stream_id, changed_dates):
        data_source = self.get_data_source()
        dates = set((self.force_precision(date) for date in changed_dates))
        rows = {}
        for date in dates:
            key = self.get_row_key(data_stream_id, date)
            rows.setdefault(key, {})
            date_range = self.get_date_range(date)
            aggregate = data_source.aggregate(
                data_stream_id,
                start_date=date_range[0],
                end_date=date_range[1]
            )
            if aggregate is not None:
                rows[key][date] = aggregate
        self.column_family.batch_insert(rows)

    def force_precision(self, date):
        raise NotImplementedError

    def get_date_range(self, date):
        raise NotImplementedError

    def get_data_source(self):
        raise NotImplementedError

class HourlyAggregates(AggregatesStore):

    _column_family_name = 'HourlyAggregates'

    def get_row_key(self, data_stream_id, date):
        if date.tzinfo is None:
            raise ValueError("Naive datetime is not supported.")
        date = pytz.utc.normalize(date.astimezone(pytz.utc)).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )
        return super(HourlyAggregates, self).get_row_key(
            data_stream_id,
            date
        )

    def force_precision(self, date):
        return date.replace(minute=0, second=0, microsecond=0)

    def get_date_range(self, date):
        return (
            date,
            (date + datetime.timedelta(hours=1) - datetime.time.resolution)
        )

    def get_data_source(self):
        return Measurements()

class DailyAggregates(AggregatesStore):

    _column_family_name = 'DailyAggregates'

    def get_row_key(self, data_stream_id, date):
        if date.tzinfo is None:
            raise ValueError("Naive datetime is not supported.")
        date = pytz.utc.normalize(date.astimezone(pytz.utc)).replace(
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )
        return super(DailyAggregates, self).get_row_key(data_stream_id, date)

    def force_precision(self, date):
        return date.replace(hour=0, minute=0, second=0, microsecond=0)

    def get_date_range(self, date):
        return (
            date,
            (date + datetime.timedelta(days=1) - datetime.time.resolution)
        )

    def get_data_source(self):
        return HourlyAggregates()

class MonthlyAggregates(AggregatesStore):

    _column_family_name = 'MonthlyAggregates'

    def get_row_key(self, data_stream_id, date):
        if date.tzinfo is None:
            raise ValueError("Naive datetime is not supported.")
        date = pytz.utc.normalize(date.astimezone(pytz.utc)).replace(
            month=1,
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )
        return super(MonthlyAggregates, self).get_row_key(data_stream_id, date)

    def force_precision(self, date):
        return date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    def get_date_range(self, date):
        end_date = date.replace(
            day=calendar.monthrange(date.year, date.month)[1],
            hour=23,
            minute=59,
            second=59,
            microsecond=999999
        )
        return (date, end_date)

    def get_data_source(self):
        return DailyAggregates()

class LastDataPoints(ColumnFamilyProxy):

    _column_family_name = 'LastDataPoints'

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
            pycassa_types.IntegerType(),
        )
        super(LastDataPoints, cls).create(
            system_manager,
            keyspace,
            **additional_kwargs
        )

    def __init__(self):
        super(LastDataPoints, self).__init__()
        self.column_family.default_validation_class = RealType()

    def update(self, feed_id, data_stream_id):
        last_data_point = Measurements().get_last_data_point(data_stream_id)
        if last_data_point is None:
            return
        date = pytz.utc.normalize(last_data_point[0].astimezone(pytz.utc))
        timestamp = (
            int(
                time.mktime(date.replace(tzinfo=None).timetuple())
                * 1000000
            )
            + date.microsecond
        )
        self.column_family.insert(
            feed_id,
            {data_stream_id: last_data_point[1]},
            timestamp=timestamp
        )

    def get_last_data_stream_data_points(self, feed_id):
        try:
            result = self.column_family.get(
                feed_id,
                include_timestamp=True
            )
        except pycassa.NotFoundException:
            return {}
        return dict(map(
            lambda x: (x[0], (self._datetime_from_timestamp(x[1][1]), x[1][0])),
            result.items()
        ))

    def get_last_data_stream_data_point(self, feed_id, data_stream_id):
        try:
            result = self.column_family.get(
                feed_id,
                columns=(data_stream_id,),
                include_timestamp=True
            ).items()[0][1]
        except pycassa.NotFoundException:
            return None
        return (self._datetime_from_timestamp(result[1]), result[0])

    def get_last_data_stream_datetime(self, feed_id):
        try:
            result = self.column_family.get(
                feed_id,
                include_timestamp=True
            )
        except pycassa.NotFoundException:
            return None
        return self._datetime_from_timestamp(max(map(
            lambda x: x[1][1],
            result.items()
        )))

    def _datetime_from_timestamp(self, timestamp):
        return pytz.utc.localize(
            datetime.datetime.fromtimestamp(
                timestamp / 1000000
            ).replace(
                microsecond=(timestamp % 1000000)
            )
        )
