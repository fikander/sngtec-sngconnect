import logging

from sngconnect.cassandra.connection_pool import get_column_family

logger = logging.getLogger(__name__)

class ColumnFamilyProxy(object):

    _column_family_name = None

    @classmethod
    def create(cls, system_manager, keyspace, **additional_kwargs):
        column_families = (
            system_manager.get_keyspace_column_families(keyspace)
        )
        if not cls._column_family_name in column_families:
            system_manager.create_column_family(
                keyspace,
                cls._column_family_name,
                **additional_kwargs
            )
            logger.info("Created %s column family." % cls._column_family_name)
        else:
            logger.info(
                "%s column family already exists." % cls._column_family_name
            )

    def __init__(self):
        self.column_family = get_column_family(self._column_family_name)

    def clear(self):
        self.column_family.truncate()
