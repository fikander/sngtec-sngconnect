from wtforms import fields, validators
from wtforms.ext.csrf.form import SecureForm as BaseSecureForm

from sngconnect.translation import _

class SecureForm(BaseSecureForm):

    def generate_csrf_token(self, csrf_context):
        return csrf_context.session.get_csrf_token()

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

class SignOutForm(SecureForm):
    pass
