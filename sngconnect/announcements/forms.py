from wtforms import fields, validators

from sngconnect.forms import SecureForm
from sngconnect.translation import _

class CreateAnnouncementForm(SecureForm):

    content = fields.TextAreaField(
        _("Content"),
        validators=(
            validators.DataRequired(),
            validators.Length(min=5, max=100000),
        )
    )
