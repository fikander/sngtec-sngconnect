import os

from babel.core import Locale
from babel.support import Format
from pyramid import events, security
from pyramid.i18n import get_locale_name

from sngconnect.database import DBSession, User
from sngconnect.accounts.forms import SignOutForm

@events.subscriber(events.BeforeRender)
def add_google_maps_api_key(event):
    event['google_maps_api_key'] = (
        event['request'].registry.settings['google_maps.api_key']
    )

@events.subscriber(events.BeforeRender)
def add_sign_out_form(event):
    event['sign_out_form'] = SignOutForm(
        csrf_context=event['request']
    )

@events.subscriber(events.BeforeRender)
def add_format(event):
    event['format'] = Format(
        Locale(get_locale_name(event['request'])),
        event['request'].registry['default_timezone']
    )

@events.subscriber(events.BeforeRender)
def add_user(event):
    user_id = security.authenticated_userid(event['request'])
    if user_id is None:
        event['user'] = None
    else:
        event['user'] = DBSession.query(User).filter(
            User.id == user_id
        ).one()

@events.subscriber(events.BeforeRender)
def add_permissions(event):
    event.update({
        'can_access_devices': security.has_permission(
            'sngconnect.devices.access',
            event['request'].context,
            event['request']
        ),
        'can_access_appearance': security.has_permission(
            'sngconnect.appearance.access',
            event['request'].context,
            event['request']
        ),
    })


@events.subscriber(events.BeforeRender)
def add_appearance_stylesheet_url(event):
    request = event['request']
    assets_path = request.registry['settings'][
        'sngconnect.appearance_assets_upload_path'
    ]
    stylesheet_filename = request.registry['settings'][
        'sngconnect.appearance_stylesheet_filename'
    ]
    event['appearance_stylesheet_url'] = request.static_url(
        os.path.join(assets_path, stylesheet_filename)
    )
