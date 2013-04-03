import re

import pytz
from wtforms import fields, validators

from sngconnect.forms import SecureForm
from sngconnect.translation import _
from sngconnect.database import DBSession, User

class AuthenticationForm(SecureForm):

    email = fields.TextField(
        _("E-mail"),
        validators=(
            validators.DataRequired(message=_("This field is required.")),
            validators.Length(max=200),
            validators.Email(),
        )
    )
    password = fields.PasswordField(
        _("Password"),
        validators=(
            validators.DataRequired(message=_("This field is required.")),
            validators.Length(max=1000),
        )
    )

class ChangePasswordForm(SecureForm):

    password = fields.PasswordField(
        _("Password"),
        validators=(
            validators.DataRequired(message=_("This field is required.")),
            validators.Length(min=5, max=1000),
        )
    )
    repeated_password = fields.PasswordField(
        _("Repeat password"),
        validators=(
            validators.DataRequired(message=_("This field is required.")),
            validators.Length(min=5, max=1000),
            validators.EqualTo('password'),
        )
    )

class AccountDataBaseForm(SecureForm):

    phone = fields.TextField(
        _("Phone number"),
        filters=(
            lambda x: None if x is None else re.sub(r'[^\+\d]', '', x),
        ),
        validators=(
            validators.DataRequired(message=_("This field is required.")),
            validators.Length(max=50),
            validators.Regexp(r'\+?\d+'),
        )
    )
    user_name = fields.TextField(
        _("Name [person]"),
        validators=(
            validators.DataRequired(message=_("This field is required.")),
            validators.Length(max=200),
        )
    )
    company_name = fields.TextField(
        _("Company name"),
        validators=(
            validators.Length(max=200),
        )
    )

    def __init__(self, *args, **kwargs):
        obj = kwargs.get('obj')
        if obj is not None:
            kwargs['user_name'] = obj.name
        super(AccountDataBaseForm, self).__init__(*args, **kwargs)

    def populate_obj(self, obj, *args, **kwargs):
        super(AccountDataBaseForm, self).populate_obj(obj, *args, **kwargs)
        self.user_name.populate_obj(obj, 'name')

class ChangeAccountDataForm(AccountDataBaseForm):

    timezone_tzname = fields.SelectField(
        _("Time zone"),
        choices=[(name, name) for name in pytz.all_timezones]
    )

class ChangeNotificationSettings(SecureForm):

    send_email_error = fields.BooleanField(_("E-mail errors"))
    send_email_warning = fields.BooleanField(_("E-mail warnings"))
    send_email_info = fields.BooleanField(_("E-mail information"))
    send_email_comment = fields.BooleanField(_("E-mail comments"))

    send_sms_error = fields.BooleanField(_("SMS errors"))
    send_sms_warning = fields.BooleanField(_("SMS warnings"))
    send_sms_info = fields.BooleanField(_("SMS information"))
    send_sms_comment = fields.BooleanField(_("SMS comments"))

class SignUpForm(AccountDataBaseForm, ChangePasswordForm):

    email = fields.TextField(
        _("E-mail"),
        validators=(
            validators.DataRequired(message=_("This field is required.")),
            validators.Length(max=200),
            validators.Email(),
        )
    )

    def validate_email(self, field):
        count = DBSession.query(User).filter(
            User.email == field.data
        ).count()
        if count != 0:
            raise validators.ValidationError(
                _("There is already an account registered with this e-mail"
                  " address.")
            )

class SignOutForm(SecureForm):
    pass

class ActivationForm(SecureForm):

    phone_activation_code = fields.TextField(
        _("Phone activation code"),
        validators=(
            validators.DataRequired(message=_("This field is required.")),
            validators.Length(max=1000)
        )
    )
