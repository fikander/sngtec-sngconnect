import logging

from pycassa.system_manager import SystemManager

logger = logging.getLogger(__name__)

def get_arguments_from_config(settings):
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

def get_system_manager(settings):
    arguments = get_arguments_from_config(settings)
    server = arguments['server_list'][0]
    manager = SystemManager(
        server,
        credentials=arguments['credentials']
    )
    logger.info(
        "Opened management connection to Cassandra server: %s" % server
    )
    return manager
