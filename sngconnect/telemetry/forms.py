import decimal

from wtforms import fields, validators
from sqlalchemy.orm import exc as database_exceptions
import babel.numbers

from sngconnect.forms import SecureForm
from sngconnect.translation import _
from sngconnect.database import DBSession, User

class LocalizedDecimalField(fields.DecimalField):

    def _value(self):
        if self.raw_data:
            return self.raw_data[0]
        elif self.data is not None:
            return babel.numbers.format_decimal(
                self.data,
                format='0.##################################################',
                locale=self.locale
            )
        else:
            return ''

    def process_formdata(self, valuelist):
        if valuelist:
            try:
                self.data = decimal.Decimal(
                    babel.numbers.parse_decimal(
                        valuelist[0],
                        locale=self.locale
                    )
                )
            except babel.numbers.NumberFormatError:
                self.data = None
                raise ValueError(self.gettext('Not a valid decimal value'))

    def set_locale(self, locale):
        self.locale = locale

class ValueForm(SecureForm):

    value = LocalizedDecimalField(
        _("Value"),
        places=None,
        validators=(
            validators.DataRequired(),
        )
    )

    def __init__(self, *args, **kwargs):
        locale = kwargs.pop('locale')
        super(ValueForm, self).__init__(*args, **kwargs)
        self.value.set_locale(locale)

class ValueBoundsForm(SecureForm):

    minimum = LocalizedDecimalField(
        _("Minimum"),
        places=None,
        validators=(
            validators.Optional(),
        )
    )
    maximum = LocalizedDecimalField(
        _("Maximum"),
        places=None,
        validators=(
            validators.Optional(),
        )
    )

    def __init__(self, *args, **kwargs):
        locale = kwargs.pop('locale')
        super(ValueBoundsForm, self).__init__(*args, **kwargs)
        self.minimum.set_locale(locale)
        self.maximum.set_locale(locale)

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
