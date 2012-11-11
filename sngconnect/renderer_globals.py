from pyramid import events, security

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
def add_user(event):
    user_id = security.authenticated_userid(event['request'])
    if user_id is None:
        event['user'] = None
    else:
        event['user'] = DBSession.query(User).filter(
            User.id == user_id
        ).one()
