from wtforms import fields, validators
from sqlalchemy.orm import exc as database_exceptions

from sngconnect.forms import SecureForm
from sngconnect.translation import _
from sngconnect.database import DBSession, User

class ValueBoundsForm(SecureForm):

    minimum = fields.DecimalField(
        _("Minimum"),
        places=None,
        validators=(
            validators.Optional(),
        )
    )
    maximum = fields.DecimalField(
        _("Maximum"),
        places=None,
        validators=(
            validators.Optional(),
        )
    )

    def validate_maximum(self, field):
        if field.errors:
            return
        if self.minimum.data > field.data:
            raise validators.ValidationError(
                _("Maximum must be greater than or equal to the minimum.")
            )

class AddFeedUserForm(SecureForm):

    email = fields.TextField(
        _("E-mail"),
        validators=(
            validators.DataRequired(),
            validators.Length(max=200),
            validators.Email(),
        )
    )

    def validate_email(self, field):
        if field.errors:
            return
        try:
            self.user = DBSession.query(User).filter(
                User.email == field.data,
                User.activated != None
            ).one()
        except database_exceptions.NoResultFound:
            raise validators.ValidationError(
                _("There is no active user having this e-mail address.")
            )

    def get_user(self):
        return self.user

class AddFeedMaintainerForm(AddFeedUserForm):
    pass
