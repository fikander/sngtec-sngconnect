import datetime
import calendar
import time

import pytz
import numpy
import pycassa
from pycassa import types as pycassa_types

from sngconnect.cassandra.column_family_proxy import ColumnFamilyProxy
from sngconnect.cassandra.types import MicrosecondTimestampType

class Alarms(ColumnFamilyProxy):

    _column_family_name = 'Alarms'

    @classmethod
    def create(cls, system_manager, keyspace, **additional_kwargs):
        additional_kwargs.setdefault(
            'super',
            True
        )
        additional_kwargs.setdefault(
            'comparator_type',
            pycassa_types.IntegerType()
        )
        additional_kwargs.setdefault(
            'subcomparator_type',
            pycassa_types.IntegerType()
        )
        additional_kwargs.setdefault(
            'default_validation_class',
            pycassa_types.IntegerType()
        )
        additional_kwargs.setdefault(
            'key_validation_class',
            pycassa_types.IntegerType()
        )
        super(Alarms, cls).create(
            system_manager,
            keyspace,
            **additional_kwargs
        )

    def __init__(self):
        super(Alarms, self).__init__()
        self.column_family.default_validation_class = MicrosecondTimestampType()

    def set_alarms_on(self, system_id, parameter_id, alarm_ids, date):
        self.column_family.insert(
            system_id,
            {
                parameter_id: {
                    alarm_id: date for alarm_id in alarm_ids
                },
            }
        )

    def set_alarms_off(self, system_id, parameter_id, alarm_ids):
        self.column_family.remove(
            system_id,
            alarm_ids,
            super_column=parameter_id
        )

    def get_active_alarms(self, system_id, parameter_id=None):
        if parameter_id is None:
            try:
                return {
                    parameter_id: {
                        alarm_id: date
                        for alarm_id, date in alarms.iteritems()
                    }
                    for parameter_id, alarms
                    in self.column_family.get(system_id).iteritems()
                }
            except pycassa.NotFoundException:
                return {}
        else:
            try:
                return {
                    alarm_id: date
                    for alarm_id, date in self.column_family.get(
                        system_id,
                        super_column=parameter_id
                    ).iteritems()
                }
            except pycassa.NotFoundException:
                return {}
