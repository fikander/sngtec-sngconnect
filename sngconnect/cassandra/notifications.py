import pycassa
from pycassa import types as pycassa_types

from sngconnect.cassandra.column_family_proxy import ColumnFamilyProxy

class Notifications(ColumnFamilyProxy):

    _column_family_name = 'Notifications'

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
        super(Notifications, cls).create(
            system_manager,
            keyspace,
            **additional_kwargs
        )

    def set_unread(self, user_ids, message_id):
        self.column_family.batch_insert(
            dict((
                (user_id, {message_id: ''})
                for user_id in user_ids
            ))
        )

    def set_read(self, user_id, message_ids):
        self.column_family.remove(user_id, message_ids)

    def get_unread(self, user_id):
        try:
            return self.column_family.get(user_id).keys()
        except pycassa.NotFoundException:
            return []
