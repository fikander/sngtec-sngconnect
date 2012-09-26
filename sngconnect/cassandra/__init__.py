import logging

from pycassa.system_manager import SIMPLE_STRATEGY

from sngconnect.cassandra import configuration, parameters, log

logger = logging.getLogger(__name__)

def initialize_keyspace(settings):
    arguments = configuration.get_arguments_from_config(settings)
    manager = configuration.get_system_manager(settings)
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
    column_family_proxy_classes = (
        parameters.Measurements,
        parameters.HourlyAggregates,
        parameters.DailyAggregates,
        parameters.MonthlyAggregates,
        parameters.MeasurementDays,
        log.Logs,
        log.LoggingDays,
    )
    for proxy_class in column_family_proxy_classes:
        proxy_class.create(manager, arguments['keyspace'])

def drop_keyspace(settings):
    arguments = configuration.get_arguments_from_config(settings)
    manager = configuration.get_system_manager(settings)
    if arguments['keyspace'] in manager.list_keyspaces():
        manager.drop_keyspace(arguments['keyspace'])
        logger.info("Dropped keyspace %s." % arguments['keyspace'])
