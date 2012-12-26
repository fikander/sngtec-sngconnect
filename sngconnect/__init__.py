import os
import errno

import pytz
import sqlalchemy
from pyramid.config import Configurator
from pyramid.session import UnencryptedCookieSessionFactoryConfig
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy

from sngconnect.database import DBSession, User
from sngconnect.routes import ROUTES
from sngconnect.assets import ASSET_BUNDLES
from sngconnect.security import RootFactory
from sngconnect import template_filters
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
    config.registry['settings'] = settings
    # Configure ACL.
    config.set_root_factory(RootFactory)
    # Configure security.
    authentication_policy = AuthTktAuthenticationPolicy(
        settings['session.secret'],
        callback=User.authentication_callback
    )
    config.set_authentication_policy(authentication_policy)
    authorization_policy = ACLAuthorizationPolicy()
    config.set_authorization_policy(authorization_policy)
    # Configure session.
    session_factory = UnencryptedCookieSessionFactoryConfig(
        settings['session.secret']
    )
    config.set_session_factory(session_factory)
    # Add translation directories.
    config.add_translation_dirs(os.path.join(
        os.path.dirname(__file__),
        'locale'
    ))
    # Set default timezone.
    config.registry['default_timezone'] = pytz.timezone(
        settings['sngconnect.default_timezone']
    )
    # Include add-ons.
    config.include('pyramid_tm')
    config.include('pyramid_jinja2')
    config.include('pyramid_webassets')
    config.include('pyramid_mailer')
    # Configure asset bundles
    for name, bundle in ASSET_BUNDLES.iteritems():
        config.add_webasset(name, bundle)
    # Add Jinja2 extensions.
    config.add_jinja2_extension('jinja2.ext.with_')
    config.add_jinja2_extension('webassets.ext.jinja2.AssetsExtension')
    jinja2_environment = config.get_jinja2_environment()
    config.registry['jinja2_environment'] = jinja2_environment
    jinja2_environment.filters.update({
        'tojson': template_filters.tojson,
        'format_datetime': template_filters.format_datetime,
        'format_date': template_filters.format_date,
        'format_time': template_filters.format_time,
        'format_number': template_filters.format_number,
        'format_decimal': template_filters.format_decimal,
    })
    jinja2_environment.assets_environment = config.get_webassets_env()
    # Configure routes.
    for name, pattern in ROUTES:
        config.add_route(name, pattern)
    # Add static views.
    config.add_static_view(
        name='static',
        path='sngconnect:static',
        cache_max_age=0
    )
    config.add_static_view(
        name='device-images',
        path=settings['sngconnect.device_image_upload_path'],
        cache_max_age=0
    )
    config.add_static_view(
        name='appearance-assets',
        path=settings['sngconnect.appearance_assets_upload_path'],
        cache_max_age=0
    )
    # Create appearance stylesheet if not exists.
    assets_path = settings['sngconnect.appearance_assets_upload_path']
    appearance_stylesheet_path = os.path.join(
        assets_path,
        settings['sngconnect.appearance_stylesheet_filename']
    )
    try:
        os.makedirs(assets_path)
    except OSError as exception:
        if (exception.errno == errno.EEXIST and
                os.path.isdir(assets_path)):
            pass
        else:
            raise
    open(appearance_stylesheet_path, 'a').close()
    # Scan for view configurations.
    config.scan()
    # Return ready WSGI application.
    return config.make_wsgi_app()
