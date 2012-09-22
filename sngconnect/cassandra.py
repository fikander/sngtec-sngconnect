import logging

from pycassa.pool import ConnectionPool
from pycassa.system_manager import SystemManager, SIMPLE_STRATEGY
from pycassa.columnfamily import ColumnFamily
from pycassa import types

# Initialized using `initialize_connection_pool()`.
_connection_pool = None

logger = logging.getLogger(__name__)

class ColumnFamilyProxy:

    _column_family_name = None

    @classmethod
    def create(cls, system_manager, keyspace):
        column_families = (
            system_manager.get_keyspace_column_families(keyspace)
        )
        if not cls._column_family_name in column_families:
            system_manager.create_column_family(
                keyspace,
                cls._column_family_name,
                comparator_type=types.DateType(),
                default_validation_class=types.UTF8Type()
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

class ParameterValues(ColumnFamilyProxy):

    _column_family_name = 'ParameterValues'

    def insert_data_points(self, parameter_id, data_points):
        rows = {}
        for measurement_datetime, value in data_points:
            key = ':'.join((
                str(parameter_id),
                measurement_datetime.date().isoformat()
            ))
            if not key in rows:
                rows[key] = {}
            rows[key][measurement_datetime] = str(value)
        self.column_family.batch_insert(rows)

def initialize_connection_pool(settings):
    global _connection_pool
    arguments = _get_arguments_from_config(settings)
    pool_size = 5 * len(arguments['server_list'])
    _connection_pool = ConnectionPool(
        arguments['keyspace'],
        server_list=arguments['server_list'],
        credentials=arguments['credentials'],
        pool_size=pool_size
    )
    logger.info("Opened %d connections to Cassandra servers: %s" % (
        pool_size,
        ', '.join(arguments['server_list'])
    ))

def get_column_family(column_family_name):
    global _connection_pool
    if _connection_pool is None:
        raise ValueError(
            "Cassandra connection pool is not configured. Use"
            " `initialize_connection_pool()` to configure it using config"
            " dictionary."
        )
    return ColumnFamily(_connection_pool, column_family_name)

def initialize_keyspace(settings):
    arguments = _get_arguments_from_config(settings)
    manager = _get_system_manager(settings)
    # Create keyspace.
    if not arguments['keyspace'] in manager.list_keyspaces():
        manager.create_keyspace(
            arguments['keyspace'],
            replication_strategy=SIMPLE_STRATEGY,
            strategy_options={
                'replication_factor': '1',
            }
        )
        logger.info("Created keyspace '%s'" % arguments['keyspace'])
    else:
        logger.info("Keyspace '%s' already exists." % arguments['keyspace'])
    # Create column families.
    ParameterValues.create(manager, arguments['keyspace'])

def drop_keyspace(settings):
    arguments = _get_arguments_from_config(settings)
    manager = _get_system_manager(settings)
    if arguments['keyspace'] in manager.list_keyspaces():
        manager.drop_keyspace(arguments['keyspace'])
        logger.info("Dropped keyspace %s." % arguments['keyspace'])

def _get_arguments_from_config(settings):
    config_key = lambda key: '.'.join(('cassandra', key))
    keyspace = settings[config_key('keyspace')]
    server_list = settings[config_key('servers')].split()
    credentials = dict(
        username=settings.get(config_key('username')),
        password=settings.get(config_key('password'))
    )
    if all(map(lambda value: value is None, credentials.values())):
        credentials = None
    return {
        'keyspace': keyspace,
        'server_list': server_list,
        'credentials': credentials,
    }

def _get_system_manager(settings):
    arguments = _get_arguments_from_config(settings)
    server = arguments['server_list'][0]
    manager = SystemManager(
        server,
        credentials=arguments['credentials']
    )
    logger.info(
        "Opened management connection to Cassandra server: %s" % server
    )
    return manager
