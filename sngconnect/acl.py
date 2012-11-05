from pyramid.traversal import DefaultRootFactory
from pyramid.security import Everyone, Authenticated, Allow

class RootFactory(DefaultRootFactory):
    __acl__ = [
        (Allow, Everyone,      'sngconnect.accounts.sign_in'),
        (Allow, Authenticated, 'sngconnect.accounts.sign_out'),
        (Allow, Everyone,      'sngconnect.accounts.sign_up'),
        (Allow, Everyone,      'sngconnect.accounts.activate'),
        (Allow, Authenticated, 'sngconnect.telemetry.access'),
    ]
