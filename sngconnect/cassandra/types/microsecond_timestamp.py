import time
import datetime

from pycassa import types, marshal

class MicrosecondTimestampType(types.IntegerType):

    def __init__(self, *args, **kwargs):
        super(MicrosecondTimestampType, self).__init__(*args, **kwargs)
        self.pack_integer = marshal.packer_for('IntegerType')
        self.unpack_integer = marshal.unpacker_for('IntegerType')

    def pack(self, datetime_value, *args, **kwargs):
        timestamp = (
            int(time.mktime(datetime_value.timetuple()) * 1000000)
            + datetime_value.microsecond
        )
        return self.pack_integer(timestamp, *args, **kwargs)

    def unpack(self, timestamp_value, *args, **kwargs):
        timestamp = self.unpack_integer(timestamp_value, *args, **kwargs)
        return datetime.datetime.fromtimestamp(
            timestamp / 1000000
        ).replace(
            microsecond=(timestamp % 1000000)
        )
