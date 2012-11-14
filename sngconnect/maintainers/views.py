import datetime

import pytz
from sqlalchemy.orm import exc as database_exceptions
from pyramid.view import view_config
from pyramid.security import effective_principals
from pyramid import httpexceptions
from pyramid_mailer import get_mailer
from pyramid_mailer.message import Message as EmailMessage

from sngconnect import security
from sngconnect.translation import _
from sngconnect.database import DBSession, User
from sngconnect.accounts import forms

@view_config(
    route_name='sngconnect.maintainers.manage',
    renderer='sngconnect.maintainers:templates/manage.jinja2',
    permission='sngconnect.maintainers.access'
)
def sing_in(request):
    add_maintainer_form = forms.AddMaintainerForm(csrf_context=request)
    if request.method == 'POST':
        add_maintainer_form.process(request.POST)
        if add_maintainer_form.validate():
            pass
    maintainers = DBSession.query(User).filter(
        User.role_maintainer == True
    ).order_by(User.email)
    if security.Supplier not in effective_principals(request):

    return {
        'add_maintainer_form': add_maintainer_form,
        'maintainers': maintainers,
    }
