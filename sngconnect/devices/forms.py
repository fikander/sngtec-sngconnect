from wtforms import fields, validators

from sngconnect.forms import SecureForm
from sngconnect.translation import _
from sngconnect.database import DBSession, FeedTemplate

class FeedTemplateForm(SecureForm):

    name = fields.TextField(
        _("Name"),
        validators=(
            validators.DataRequired(),
            validators.Length(max=200),
        )
    )

    def validate_name(self, field):
        if field.errors:
            return
        count = DBSession.query(FeedTemplate).filter(
            FeedTemplate.name == field.data
        ).count()
        if count > 0:
            raise validators.ValidationError(
                _("There is already device template having this name.")
            )
