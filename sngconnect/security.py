from pyramid.traversal import DefaultRootFactory
from pyramid.security import Everyone, Authenticated, Allow

User = 'sngconnect.security.User'
Maintainer = 'sngconnect.security.Maintainer'
Supplier = 'sngconnect.security.Supplier'
Administrator = 'sngconnect.security.Administrator'

class RootFactory(DefaultRootFactory):
    __acl__ = [
        (Allow, Everyone,      'sngconnect.accounts.sign_in'),
        (Allow, Authenticated, 'sngconnect.accounts.sign_out'),
        (Allow, Everyone,      'sngconnect.accounts.sign_up'),
        (Allow, Everyone,      'sngconnect.accounts.activate'),
        (Allow, Authenticated, 'sngconnect.accounts.settings'),
        (Allow, Authenticated, 'sngconnect.telemetry.access'),
        (Allow, Authenticated, 'sngconnect.telemetry.create_feed'),
        (Allow, Administrator, 'sngconnect.telemetry.access_all'),
        (Allow, Administrator, 'sngconnect.telemetry.change_all'),
        (Allow, Authenticated, 'sngconnect.payments.access'),
        (Allow, Supplier,      'sngconnect.devices.access'),
        (Allow, Administrator, 'sngconnect.devices.access'),
        (Allow, Supplier,      'sngconnect.appearance.access'),
        (Allow, Administrator, 'sngconnect.appearance.access'),
        (Allow, Supplier,      'sngconnect.announcements.access'),
        (Allow, Administrator, 'sngconnect.announcements.access'),
    ]
