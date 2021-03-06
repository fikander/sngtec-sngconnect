import datetime

import pytz
from sqlalchemy.orm import exc as database_exceptions
from pyramid.view import view_config
from pyramid import security
from pyramid import httpexceptions
from pyramid_mailer import get_mailer
from pyramid_mailer.message import Message as EmailMessage

from sngconnect.translation import _
from sngconnect.database import DBSession, User
from sngconnect.services.sms import SMSService
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
                    User.email == sign_in_form.email.data.lower()
                ).one()
            except database_exceptions.NoResultFound:
                request.session.flash(
                    _("Invalid credentials."),
                    queue='error'
                )
            else:
                if user.activated is None:
                    request.session.flash(
                        _("This account is currently inactive."
                          " Please follow the instructions we sent you on"
                          " your e-mail address."),
                        queue='error'
                    )
                elif user.validate_password(sign_in_form.password.data):
                    headers = security.remember(request, user.id)
                    return httpexceptions.HTTPFound(
                        destination,
                        headers=headers
                    )
                else:
                    request.session.flash(
                        _("Invalid credentials."),
                        queue='error'
                    )
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
                email=sign_up_form.email.data.lower(),
                phone=sign_up_form.phone.data,
                name=sign_up_form.user_name.data,
                company_name=(
                    sign_up_form.company_name.data
                    if sign_up_form.company_name.data else
                    None
                ),
                timezone_tzname=str(request.registry['default_timezone'])
            )
            user.set_password(sign_up_form.password.data)
            DBSession.add(user)
            template = request.registry['jinja2_environment'].get_template(
                'sngconnect.accounts:templates/emails/account_activation.txt'
            )
            activation_email = EmailMessage(
                subject=_("Activate your account at SNG Connect"),
                sender=request.registry['settings']['mail.sender'],
                recipients=[user.email],
                body=template.render(
                    activation_url=request.route_url(
                        'sngconnect.accounts.activate',
                        email=user.email,
                        email_activation_code=user.email_activation_code
                    )
                )
            )
            get_mailer(request).send(activation_email)
            sms_service = SMSService(request.registry)
            sms_service.send_sms(
                [user.phone],
                _(
                    "Your SNG:connect confirmation code is: ${code}",
                    mapping={
                        'code': user.phone_activation_code,
                    }
                )
            )
            successful_submission = True
    return {
        'sign_up_form': sign_up_form,
        'successful_submission': successful_submission,
    }


@view_config(
    route_name='sngconnect.accounts.activate',
    renderer='sngconnect.accounts:templates/activate.jinja2',
    permission='sngconnect.accounts.activate'
)
def activate(request):
    successful_activation = False
    try:
        user = DBSession.query(User).filter(
            User.email == request.matchdict['email'],
            User.email_activation_code ==
                request.matchdict['email_activation_code'],
            User.activated == None
        ).one()
    except database_exceptions.NoResultFound:
        raise httpexceptions.HTTPNotFound()
    activation_form = forms.ActivationForm(csrf_context=request)
    if request.method == 'POST':
        activation_form.process(request.POST)
        if activation_form.validate():
            if (user.phone_activation_code.upper() !=
                    activation_form.phone_activation_code.data.upper()):
                request.session.flash(
                    _("The activation code you entered is invalid."),
                    queue='error'
                )
            else:
                # Regenerate activation code so user cannot reactivate his
                # account after being banned.
                user.regenerate_email_activation_code()
                user.activated = pytz.utc.localize(datetime.datetime.utcnow())
                DBSession.add(user)
                successful_activation = True
    return {
        'activation_form': activation_form,
        'successful_activation': successful_activation,
    }


@view_config(
    route_name='sngconnect.accounts.settings',
    renderer='sngconnect.accounts:templates/settings.jinja2',
    permission='sngconnect.accounts.settings'
)
def settings(request):
    user = DBSession.query(User).filter(
        User.id == security.authenticated_userid(request)
    ).one()
    change_account_data_form = forms.ChangeAccountDataForm(
        obj=user,
        csrf_context=request
    )
    change_notification_settings_form = forms.ChangeNotificationSettings(
        obj=user,
        csrf_context=request
    )
    change_password_form = forms.ChangePasswordForm(csrf_context=request)
    if request.method == 'POST':
        if 'submit_change_account_data' in request.POST:
            change_account_data_form.process(request.POST)
            if change_account_data_form.validate():
                change_account_data_form.populate_obj(user)
                DBSession.add(user)
                request.session.flash(
                    _("Your account data has been successfully changed."),
                    queue='success'
                )
                return httpexceptions.HTTPFound(
                    request.route_url('sngconnect.accounts.settings')
                )
        if 'submit_change_notification_settings' in request.POST:
            change_notification_settings_form.process(request.POST)
            if change_notification_settings_form.validate():
                change_notification_settings_form.populate_obj(user)
                DBSession.add(user)
                request.session.flash(
                    _(
                        "Your notification settings have been successfully"
                        " changed."
                    ),
                    queue='success'
                )
                return httpexceptions.HTTPFound(
                    request.route_url('sngconnect.accounts.settings')
                )
        elif 'submit_change_password' in request.POST:
            change_password_form.process(request.POST)
            if change_password_form.validate():
                user.set_password(change_password_form.password.data)
                DBSession.add(user)
                request.session.flash(
                    _("Your password has been successfully changed."),
                    queue='success'
                )
                return httpexceptions.HTTPFound(
                    request.route_url('sngconnect.accounts.settings')
                )
        request.session.flash(
            _(
                "There were some problems with your request."
                " Please check the form for error messages."
            ),
            queue='error'
        )
    return {
        'change_account_data_form': change_account_data_form,
        'change_notification_settings_form': change_notification_settings_form,
        'change_password_form': change_password_form,
    }
