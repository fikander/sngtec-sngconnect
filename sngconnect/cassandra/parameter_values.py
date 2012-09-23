import datetime

import pycassa
from pycassa import types as pycassa_types

from sngconnect.cassandra.types.microsecond_timestamp import (
    MicrosecondTimestampType)
from sngconnect.cassandra.column_family_proxy import ColumnFamilyProxy

class ParameterValues(ColumnFamilyProxy):

    _column_family_name = 'ParameterValues'

    def __init__(self):
        super(ParameterValues, self).__init__()
        self.column_family.column_name_class = MicrosecondTimestampType()

    @classmethod
    def create(cls, system_manager, keyspace, **additional_kwargs):
        additional_kwargs.setdefault(
            'comparator_type',
            pycassa_types.IntegerType()
        )
        additional_kwargs.setdefault(
            'default_validation_class',
            pycassa_types.DecimalType()
        )
        additional_kwargs.setdefault(
            'key_validation_class',
            pycassa_types.CompositeType(
                pycassa_types.IntegerType(),
                pycassa_types.DateType()
            )
        )
        super(ParameterValues, cls).create(
            system_manager,
            keyspace,
            **additional_kwargs
        )

    def insert_data_points(self, parameter_id, data_points):
        rows = {}
        key_index = ParameterValuesKeyIndex()
        for measurement_datetime, value in data_points:
            key = self._row_key(parameter_id, measurement_datetime.date())
            rows.setdefault(key, {})
            rows[key][measurement_datetime] = value
        self.column_family.batch_insert(rows)
        key_index.add_dates(
            parameter_id,
            (date for date, value in data_points)
        )

    def get_data_points(self, parameter_id, start_date=None, end_date=None):
        if start_date is None:
            start_date = datetime.datetime.min
        if end_date is None:
            end_date = datetime.datetime.max
        # Setting column count to Cassandra's maximum. We assume that
        # clients of this API know what they're doing.
        column_count = 2000000000
        if start_date.date() == end_date.date():
            # Data points from single day requested, we don't need to use
            # multiget.
            result = self.column_family.get(
                self._row_key(parameter_id, start_date.date()),
                column_start=start_date,
                column_finish=end_date,
                column_count=column_count
            )
            return result.items()
        else:
            # Data points from possibly many days request, we have to use
            # multiget.
            key_index = ParameterValuesKeyIndex()
            dates = key_index.get_dates(
                parameter_id,
                start_date=start_date,
                end_date=end_date
            )
            keys = [self._row_key(parameter_id, date) for date in dates]
            result = self.column_family.multiget(
                keys,
                column_start=start_date,
                column_finish=end_date,
                column_count=column_count
            )
            data_points = []
            for key, columns in result.iteritems():
                data_points += columns.items()
            return data_points

    @classmethod
    def _row_key(cls, parameter_id, date):
        if isinstance(date, datetime.date):
            date = datetime.datetime.combine(date, datetime.time.min)
        return (parameter_id, date)

class ParameterValuesKeyIndex(ColumnFamilyProxy):

    _column_family_name = 'ParameterValuesKeyIndex'

    @classmethod
    def create(cls, system_manager, keyspace, **additional_kwargs):
        additional_kwargs.setdefault(
            'comparator_type',
            pycassa_types.IntegerType()
        )
        additional_kwargs.setdefault(
            'default_validation_class',
            pycassa_types.BytesType()
        )
        additional_kwargs.setdefault(
            'key_validation_class',
            pycassa_types.IntegerType()
        )
        super(ParameterValuesKeyIndex, cls).create(
            system_manager,
            keyspace,
            **additional_kwargs
        )

    def __init__(self):
        super(ParameterValuesKeyIndex, self).__init__()
        self.column_family.column_name_class = MicrosecondTimestampType()

    def add_dates(self, parameter_id, dates):
        values = dict((
            (datetime.datetime.combine(date, datetime.time.min), '')
            for date
            in set((date.date() for date in dates))
        ))
        self.column_family.insert(parameter_id, values)

    def get_dates(self, parameter_id, start_date=None, end_date=None):
        if start_date is None:
            start_date = datetime.datetime.min
        if end_date is None:
            end_date = datetime.datetime.max
        try:
            dates = self.column_family.get(
                parameter_id,
                column_start=start_date,
                column_finish=end_date
            ).keys()
            return [date.date() for date in dates]
        except pycassa.NotFoundException:
            return []
