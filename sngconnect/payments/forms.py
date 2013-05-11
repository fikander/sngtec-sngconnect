from wtforms import fields, validators

from sngconnect.forms import SecureForm
from sngconnect.translation import _

class BuyForm(SecureForm):

    tokens = fields.IntegerField(
        _("Tokens"),
        validators=(
            validators.DataRequired(message=_("This field is required.")),
        )
    )

    def __init__(self, *args, **kwargs):
        self._order_maximum = kwargs.pop('order_maximum')
        super(BuyForm, self).__init__(*args, **kwargs)

    def validate_tokens(self, field):
        if field.data < 1:
            raise validators.ValidationError(
                _("How many tokens would you like to buy?")
            );
        if field.data > self._order_maximum:
            raise validators.ValidationError(
                _(
                    "You can only buy maximum of ${maximum} tokens at once.",
                    mapping={
                        'maximum': self._order_maximum,
                    }
                )
            );
