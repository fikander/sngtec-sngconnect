import re

from wtforms import fields, validators

from sngconnect.forms import SecureForm
from sngconnect.translation import _
from sngconnect.database import DBSession, User

class AuthenticationForm(SecureForm):

    email = fields.TextField(
        _("E-mail"),
        validators=(
            validators.DataRequired(),
            validators.Length(max=200),
            validators.Email(),
        )
    )
    password = fields.PasswordField(
        _("Password"),
        validators=(
            validators.DataRequired(),
            validators.Length(max=1000),
        )
    )

class SignUpForm(SecureForm):

    email = fields.TextField(
        _("E-mail"),
        validators=(
            validators.DataRequired(),
            validators.Length(max=200),
            validators.Email(),
        )
    )
    password = fields.PasswordField(
        _("Password"),
        validators=(
            validators.DataRequired(),
            validators.Length(min=5, max=1000),
        )
    )
    repeated_password = fields.PasswordField(
        _("Repeat password"),
        validators=(
            validators.DataRequired(),
            validators.Length(min=5, max=1000),
            validators.EqualTo('password'),
        )
    )
    phone_number = fields.TextField(
        _("Phone number"),
        filters=(
            lambda x: None if x is None else re.sub(r'[^\+\d]', '', x),
        ),
        validators=(
            validators.DataRequired(),
            validators.Length(max=50),
            validators.Regexp(r'\+?\d+'),
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
            validators.DataRequired(),
            validators.Length(max=1000)
        )
    )
