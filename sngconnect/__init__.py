import sqlalchemy
from pyramid.config import Configurator

from sngconnect.database import DBSession
from sngconnect.routes import ROUTES
from sngconnect.cassandra import connection_pool as cassandra_connection_pool

def main(global_config, **settings):
    # Configure the database connection.
    database_engine = sqlalchemy.engine_from_config(settings, 'database.')
    DBSession.configure(bind=database_engine)
    # Configure Cassandra connection.
    cassandra_connection_pool.initialize_connection_pool(settings)
    # Create application configurator.
    config = Configurator(settings=settings)
    # Include add-ons.
    config.include('pyramid_tm')
    config.include('pyramid_jinja2')
    # Configure routes.
    for name, pattern in ROUTES:
        config.add_route(name, pattern)
    # Add static view.
    config.add_static_view('static', 'static', cache_max_age=0)
    # Scan for view configurations.
    config.scan()
    # Return ready WSGI application.
    return config.make_wsgi_app()
