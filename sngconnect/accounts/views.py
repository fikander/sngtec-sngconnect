from sqlalchemy.orm import exc as database_exceptions
from pyramid.view import view_config
from pyramid import security
from pyramid import httpexceptions

from sngconnect.translation import _
from sngconnect.database import DBSession, User
from sngconnect.accounts import forms

@view_config(
    route_name='sngconnect.accounts.sign_in',
    renderer='sngconnect.accounts:templates/sign_in.jinja2',
    permission='sngconnect.accounts.sign_in'
)
def sing_in(request):
    destination = request.GET.get(
        'destination',
        request.route_url('sngconnect.telemetry.dashboard')
    )
    sign_in_form = forms.AuthenticationForm(csrf_context=request)
    if request.method == 'POST':
        sign_in_form.process(request.POST)
        if sign_in_form.validate():
            try:
                user = DBSession.query(User).filter(
                    User.email == sign_in_form.email.data
                ).one()
            except database_exceptions.NoResultFound:
                request.session.flash(
                    _("Invalid credentials."),
                    queue='error'
                )
            else:
                if user.validate_password(sign_in_form.password.data):
                    headers = security.remember(request, user.id)
                    raise httpexceptions.HTTPFound(destination, headers=headers)
    return {
        'sign_in_form': sign_in_form,
    }

@view_config(
    route_name='sngconnect.accounts.sign_out',
    request_method='POST',
    permission='sngconnect.accounts.sign_out'
)
def sing_out(request):
    sign_out_form = forms.SignOutForm(
        request.POST,
        csrf_context=request
    )
    if sign_out_form.validate():
        headers = security.forget(request)
    else:
        raise httpexceptions.HTTPBadRequest()
    return httpexceptions.HTTPSeeOther(
        request.route_url('sngconnect.accounts.sign_in'),
        headers=headers
    )

@view_config(
    route_name='sngconnect.accounts.sign_up',
    renderer='sngconnect.accounts:templates/sign_up.jinja2',
    permission='sngconnect.accounts.sign_up'
)
def sing_up(request):
    sign_up_form = forms.SignUpForm(csrf_context=request)
    successful_submission = False
    if request.method == 'POST':
        sign_up_form.process(request.POST)
        if sign_up_form.validate():
            user = User(
                email=sign_up_form.email.data,
                phone=sign_up_form.phone_number.data
            )
            user.set_password(sign_up_form.password.data)
            DBSession.add(user)
            successful_submission = True
    return {
        'sign_up_form': sign_up_form,
        'successful_submission': successful_submission,
    }
