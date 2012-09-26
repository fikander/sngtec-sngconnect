import datetime

from pycassa import types as pycassa_types

from sngconnect.cassandra.time_series import TimeSeries, TimeSeriesDateIndex

class LoggingDays(TimeSeriesDateIndex):

    _column_family_name = 'LoggingDays'

    @classmethod
    def create(cls, system_manager, keyspace, **additional_kwargs):
        additional_kwargs.setdefault(
            'key_validation_class',
            pycassa_types.AsciiType()
        )
        super(LoggingDays, cls).create(
            system_manager,
            keyspace,
            **additional_kwargs
        )

class Logs(TimeSeries):

    _column_family_name = 'Logs'
    _date_index_class = LoggingDays

    def __init__(self):
        super(Logs, self).__init__()
        self.column_family.default_validation_class = pycassa_types.UTF8Type()

    @classmethod
    def create(cls, system_manager, keyspace, **additional_kwargs):
        additional_kwargs.setdefault(
            'default_validation_class',
            pycassa_types.UTF8Type()
        )
        additional_kwargs.setdefault(
            'key_validation_class',
            pycassa_types.CompositeType(
                pycassa_types.AsciiType(),
                pycassa_types.DateType()
            ),
        )
        super(Logs, cls).create(
            system_manager,
            keyspace,
            **additional_kwargs
        )

    def get_log_entries(self, log_id, start_date=None, end_date=None):
        return super(Logs, self).get_data_points(
            log_id,
            start_date=start_date,
            end_date=end_date
        )

    def insert_log_entries(self, log_id, log_entries):
        rows = {}
        for measurement_datetime, message in log_entries:
            key = self.get_row_key(log_id, measurement_datetime)
            rows.setdefault(key, {})
            rows[key][measurement_datetime] = message
        self.column_family.batch_insert(rows)
        self._date_index_class().add_days(
            log_id,
            (date for date, value in log_entries)
        )

    def get_row_key(self, log_id, date):
        if isinstance(date, datetime.date):
            date = datetime.datetime.combine(date, datetime.time.min)
        elif isinstance(date, datetime.datetime):
            date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            raise ValueError(
                "`date` parameter must be a `datetime.date` or"
                " `datetime.datetime` object."
            )
        return super(Logs, self).get_row_key(log_id, date)
