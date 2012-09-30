import os

import sqlalchemy
from pyramid.config import Configurator

from sngconnect.database import DBSession
from sngconnect.routes import ROUTES
from sngconnect.assets import ASSET_BUNDLES
from sngconnect.cassandra import connection_pool as cassandra_connection_pool

def main(global_config, **settings):
    # Provide deployment-independent settings
    settings.update({
        # Webassets
        'webassets.base_dir': os.path.join(
            os.path.abspath(os.path.dirname(__file__)),
            'static'
        ),
        'webassets.base_url': '/static/',
        # Jinja2
        'jinja2.i18n.domain': 'sngconnect',
    })
    # Configure the database connection.
    database_engine = sqlalchemy.engine_from_config(settings, 'database.')
    DBSession.configure(bind=database_engine)
    # Configure Cassandra connection.
    cassandra_connection_pool.initialize_connection_pool(settings)
    # Create application configurator.
    config = Configurator(settings=settings)
    # Add translation directories.
    config.add_translation_dirs(os.path.join(
        os.path.dirname(__file__),
        'locale'
    ))
    # Include add-ons.
    config.include('pyramid_tm')
    config.include('pyramid_jinja2')
    config.include('pyramid_webassets')
    # Configure asset bundles
    for name, bundle in ASSET_BUNDLES.iteritems():
        config.add_webasset(name, bundle)
    # Add webassets extension to Jinja2
    config.add_jinja2_extension('webassets.ext.jinja2.AssetsExtension')
    webassets_environment = config.get_webassets_env()
    config.get_jinja2_environment().assets_environment = webassets_environment
    # Configure routes.
    for name, pattern in ROUTES:
        config.add_route(name, pattern)
    # Add static view.
    config.add_static_view('static', 'static', cache_max_age=0)
    # Scan for view configurations.
    config.scan()
    # Return ready WSGI application.
    return config.make_wsgi_app()
