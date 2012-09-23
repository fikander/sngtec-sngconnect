import datetime
import decimal

import pycassa
from pycassa import types as pycassa_types

from sngconnect.cassandra.types.microsecond_timestamp import (
    MicrosecondTimestampType)
from sngconnect.cassandra.column_family_proxy import ColumnFamilyProxy

class DataPointStore(ColumnFamilyProxy):

    def __init__(self):
        super(DataPointStore, self).__init__()
        self.column_family.column_name_class = MicrosecondTimestampType()

    @classmethod
    def create(cls, system_manager, keyspace, **additional_kwargs):
        additional_kwargs.update({
            'comparator_type': pycassa_types.IntegerType(),
            'default_validation_class': pycassa_types.DecimalType(),
            'key_validation_class': pycassa_types.CompositeType(
                pycassa_types.IntegerType(),
                pycassa_types.DateType()
            ),
        })
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
            keys = [self.get_row_key(parameter_id, date) for date in dates]
            result = self.column_family.multiget(keys, **kwargs)
            return sum((columns.items() for columns in result.values()), [])

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
            date = date.replace(
                hour=0,
                minute=0,
                second=0,
                microsecond=0
            )
        return super(Measurements, self).get_row_key(parameter_id, date)

class AveragesStore(DataPointStore):

    def force_precision(self, date):
        raise NotImplementedError

    def get_date_range(self, date):
        raise NotImplementedError

    def recalculate_averages(self, parameter_id, changed_dates):
        measurements = Measurements()
        dates = list(set((
            self.force_precision(date) for date in changed_dates
        )))
        rows = {}
        for date in dates:
            key = self.get_row_key(parameter_id, date)
            rows.setdefault(key, {})
            date_range = self.get_date_range(date)
            data_points = measurements.get_data_points(
                parameter_id,
                start_date=date_range[0],
                end_date=date_range[1]
            )
            values = (value for date, value in data_points)
            average = sum(values, decimal.Decimal(0)) / len(data_points)
            rows[key][date] = average
        self.column_family.batch_insert(rows)

class HourlyAverages(AveragesStore):

    _column_family_name = 'HourlyAverages'

    def get_row_key(self, parameter_id, date):
        if isinstance(date, datetime.date):
            date = datetime.datetime.combine(date, datetime.time.min)
        else:
            date = date.replace(
                hour=0,
                minute=0,
                second=0,
                microsecond=0
            )
        return super(HourlyAverages, self).get_row_key(parameter_id, date)

    def force_precision(self, date):
        return date.replace(
            minute=0,
            second=0,
            microsecond=0
        )

    def get_date_range(self, date):
        return (
            date,
            (date + datetime.timedelta(hours=1) - datetime.time.resolution)
        )

class DailyAverages(AveragesStore):

    _column_family_name = 'DailyAverages'

    def get_row_key(self, parameter_id, date):
        if isinstance(date, datetime.date):
            date = date.replace(
                day=1
            )
        else:
            date = date.replace(
                day=1,
                hour=0,
                minute=0,
                second=0,
                microsecond=0
            )
        return super(HourlyAverages, self).get_row_key(parameter_id, date)

    def force_precision(self, date):
        return date.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )

    def get_date_range(self, date):
        return (
            date,
            (date + datetime.timedelta(days=1) - datetime.time.resolution)
        )

class MonthlyAverages(AveragesStore):

    _column_family_name = 'MonthlyAverages'

    def get_row_key(self, parameter_id, date):
        if isinstance(date, datetime.date):
            date = date.replace(
                month=1,
                day=1
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
        return super(MonthlyAverages, self).get_row_key(parameter_id, date)

    def force_precision(self, date):
        return date.replace(
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )

    def get_date_range(self, date):
        return (
            date,
            (date + datetime.timedelta(months=1) - datetime.time.resolution)
        )

class YearlyAverages(AveragesStore):

    _column_family_name = 'YearlyAverages'

    def get_row_key(self, parameter_id, date):
        return super(MonthlyAverages, self).get_row_key(
            parameter_id,
            datetime.datetime.min
        )

    def force_precision(self, date):
        return date.replace(
            month=1,
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )

    def get_date_range(self, date):
        return (
            date,
            (date + datetime.timedelta(years=1) - datetime.time.resolution)
        )

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
            kwargs['column_start'] = start_date
        if end_date is not None:
            kwargs['column_finish'] = end_date
        try:
            dates = self.column_family.get(parameter_id, **kwargs).keys()
            return [date.date() for date in dates]
        except pycassa.NotFoundException:
            return []
