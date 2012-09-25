import datetime
import calendar

import numpy
import pycassa
from pycassa import types as pycassa_types

from sngconnect.cassandra.types import RealType, MicrosecondTimestampType
from sngconnect.cassandra.column_family_proxy import ColumnFamilyProxy

__all__ = (
    'Measurements',
    'MeasurementDays',
    'HourlyAggregates',
    'DailyAggregates',
    'MonthlyAggregates',
    'YearlyAggregates',
)

class DataPointStore(ColumnFamilyProxy):

    def __init__(self):
        super(DataPointStore, self).__init__()
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
        super(DataPointStore, cls).create(
            system_manager,
            keyspace,
            **additional_kwargs
        )

    def get_data_points(self, parameter_id, start_date=None, end_date=None):
        kwargs = {
            # Setting column count to Cassandra's maximum. We assume that
            # clients of this API know what they're doing.
            'column_count': 2000000000,
        }
        if start_date is not None:
            kwargs['column_start'] = start_date
            start_day = start_date.date()
        else:
            start_day = None
        if end_date is not None:
            kwargs['column_finish'] = end_date
            end_day = end_date.date()
        else:
            end_day = None
        if start_day is not None and start_day == end_day:
            return self.column_family.get(
                self.get_row_key(parameter_id, start_date),
                **kwargs
            ).items()
        else:
            measurement_days = MeasurementDays()
            dates = measurement_days.get_days(
                parameter_id,
                start_date=start_date,
                end_date=end_date
            )
            keys = [
                self.get_row_key(parameter_id, date) for date in dates
            ]
            result = self.column_family.multiget(keys, **kwargs)
            return sum((columns.items() for columns in result.values()), [])

    def aggregate(self, parameter_id, start_date=None, end_date=None):
        kwargs = {}
        if start_date is not None:
            kwargs['column_start'] = start_date
        if end_date is not None:
            kwargs['column_finish'] = end_date
        measurement_days = MeasurementDays()
        dates = measurement_days.get_days(
            parameter_id,
            start_date=start_date,
            end_date=end_date
        )
        keys = set((self.get_row_key(parameter_id, date) for date in dates))
        count = sum(
            self.column_family.multiget_count(keys, **kwargs).viewvalues()
        )
        if count == 0:
            return None
        values_sum = numpy.float128(0);
        minimum = None
        maximum = None
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
            if minimum is None:
                minimum = local_minimum
            else:
                minimum = min(minimum, local_minimum)
            if maximum is None:
                maximum = local_maximum
            else:
                maximum = max(maximum, local_maximum)
        result = {
            'sum': str(values_sum),
            'count': str(count),
        }
        if maximum is not None:
            result['maximum'] = str(maximum)
        if minimum is not None:
            result['minimum'] = str(minimum)
        return result

    def get_row_key(self, parameter_id, date):
        return (parameter_id, date)

class Measurements(DataPointStore):

    _column_family_name = 'Measurements'

    def insert_data_points(self, parameter_id, data_points):
        rows = {}
        measurement_days = MeasurementDays()
        for measurement_datetime, value in data_points:
            key = self.get_row_key(parameter_id, measurement_datetime)
            rows.setdefault(key, {})
            rows[key][measurement_datetime] = value
        self.column_family.batch_insert(rows)
        measurement_days.add_days(
            parameter_id,
            (date for date, value in data_points)
        )

    def get_row_key(self, parameter_id, date):
        if isinstance(date, datetime.date):
            date = datetime.datetime.combine(date, datetime.time.min)
        else:
            date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        return super(Measurements, self).get_row_key(parameter_id, date)

class AggregatesStore(DataPointStore):

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

    def get_data_points(self, parameter_id, start_date=None, end_date=None):
        if start_date is not None:
            start_date = self.force_precision(start_date)
        if end_date is not None:
            end_date = self.force_precision(end_date)
        return super(AggregatesStore, self).get_data_points(
            parameter_id,
            start_date,
            end_date
        )

    def aggregate(self, parameter_id, start_date=None, end_date=None):
        kwargs = {}
        if start_date is not None:
            kwargs['column_start'] = start_date
        if end_date is not None:
            kwargs['column_finish'] = end_date
        measurement_days = MeasurementDays()
        dates = measurement_days.get_days(
            parameter_id,
            start_date=start_date,
            end_date=end_date
        )
        keys = set((self.get_row_key(parameter_id, date) for date in dates))
        values_sum = numpy.float128(0);
        minimum = None
        maximum = None
        count = numpy.float128(0)
        for key in keys:
            try:
                result= map(
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
            count += aggregates[:,2].sum()
            values_sum += aggregates[:,3].sum()
            if minimum is None:
                minimum = local_minimum
            else:
                minimum = min(minimum, local_minimum)
            if maximum is None:
                maximum = local_maximum
            else:
                maximum = max(maximum, local_maximum)
        result = {
            'sum': str(values_sum),
            'count': str(count),
        }
        if maximum is not None:
            result['maximum'] = str(maximum)
        if minimum is not None:
            result['minimum'] = str(minimum)
        return result

    def recalculate_aggregates(self, parameter_id, changed_dates):
        data_source = self.get_data_source()
        dates = set((self.force_precision(date) for date in changed_dates))
        rows = {}
        for date in dates:
            key = self.get_row_key(parameter_id, date)
            rows.setdefault(key, {})
            date_range = self.get_date_range(date)
            aggregate = data_source.aggregate(
                parameter_id,
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

    def get_row_key(self, parameter_id, date):
        if isinstance(date, datetime.date):
            start_date = datetime.datetime.combine(date, datetime.time.min)
        else:
            start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        return super(HourlyAggregates, self).get_row_key(
            parameter_id,
            start_date
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

    def get_row_key(self, parameter_id, date):
        if isinstance(date, datetime.date):
            date = datetime.datetime.combine(
                date.replace(day=1),
                datetime.time.min
            )
        else:
            date = date.replace(
                day=1,
                hour=0,
                minute=0,
                second=0,
                microsecond=0
            )
        return super(DailyAggregates, self).get_row_key(parameter_id, date)

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

    def get_row_key(self, parameter_id, date):
        if isinstance(date, datetime.date):
            date = datetime.datetime.combine(
                date.replace(month=1, day=1),
                datetime.time.min
            )
        else:
            date = date.replace(
                month=1,
                day=1,
                hour=0,
                minute=0,
                second=0,
                microsecond=0
            )
        return super(MonthlyAggregates, self).get_row_key(parameter_id, date)

    def force_precision(self, date):
        return date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    def get_date_range(self, date):
        end_day = date.replace(
            day=calendar.monthrange(date.year, date.month)[1]
        ).date()
        end_date = datetime.datetime.combine(end_day, datetime.time.max)
        return (date, end_date)

    def get_data_source(self):
        return DailyAggregates()

class MeasurementDays(ColumnFamilyProxy):

    _column_family_name = 'MeasurementDays'

    @classmethod
    def create(cls, system_manager, keyspace, **additional_kwargs):
        additional_kwargs.update({
            'comparator_type': pycassa_types.DateType(),
            'default_validation_class': pycassa_types.BytesType(),
            'key_validation_class': pycassa_types.IntegerType(),
        })
        super(MeasurementDays, cls).create(
            system_manager,
            keyspace,
            **additional_kwargs
        )

    def add_days(self, parameter_id, dates):
        values = dict((
            (datetime.datetime.combine(day, datetime.time.min), '')
            for day
            in set((date.date() for date in dates))
        ))
        self.column_family.insert(parameter_id, values)

    def get_days(self, parameter_id, start_date=None, end_date=None):
        kwargs = {}
        if start_date is not None:
            kwargs['column_start'] = datetime.datetime.combine(
                start_date.date(),
                datetime.time.min
            )
        if end_date is not None:
            kwargs['column_finish'] = datetime.datetime.combine(
                end_date,
                datetime.time.max
            )
        try:
            dates = self.column_family.get(parameter_id, **kwargs).keys()
            return [date.date() for date in dates]
        except pycassa.NotFoundException:
            return []
