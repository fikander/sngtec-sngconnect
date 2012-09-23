import logging

from pycassa.pool import ConnectionPool
from pycassa.columnfamily import ColumnFamily

from sngconnect.cassandra.configuration import get_arguments_from_config

# Initialized using `initialize_connection_pool()`.
CONNECTION_POOL = None

logger = logging.getLogger(__name__)

def initialize_connection_pool(settings):
    global CONNECTION_POOL
    arguments = get_arguments_from_config(settings)
    pool_size = 5 * len(arguments['server_list'])
    CONNECTION_POOL = ConnectionPool(
        arguments['keyspace'],
        server_list=arguments['server_list'],
        credentials=arguments['credentials'],
        pool_size=pool_size
    )
    logger.debug("Opened %d connections to Cassandra servers: %s" % (
        pool_size,
        ', '.join(arguments['server_list'])
    ))

def get_column_family(column_family_name):
    global CONNECTION_POOL
    if CONNECTION_POOL is None:
        raise ValueError(
            "Cassandra connection pool is not configured. Use"
            " `initialize_connection_pool()` to configure it using config"
            " dictionary."
        )
    return ColumnFamily(CONNECTION_POOL, column_family_name)
