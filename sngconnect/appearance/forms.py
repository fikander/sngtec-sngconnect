import os
import re

from wtforms import fields, widgets, validators

from sngconnect.forms import SecureForm
from sngconnect.translation import _

ASSET_FILENAME_RE = re.compile(r'^[\w\-]+\.[\w\-]+$')
ASSET_FILENAME_LENGTH = 50

class UpdateStylesheetForm(SecureForm):

    stylesheet = fields.TextAreaField(
        _("Stylesheet"),
        validators=(
            validators.Length(max=500000),
        )
    )

class UploadAssetForm(SecureForm):

    ALLOWED_MIMETYPES = (
        'image/png',
        'image/jpeg',
    )

    new_file = fields.FileField(
        _("Image file"),
        description=_("Only PNG and JPG formats are allowed."),
    )

    def __init__(self, assets_path, *args, **kwargs):
        super(UploadAssetForm, self).__init__(*args, **kwargs)
        self.disallow_filenames = set(kwargs.pop('disallow_filenames', []))
        self.disallow_filenames.add('robots.txt')
        self.assets_path = assets_path

    def validate_new_file(self, field):
        if field.errors or field.data == u'':
            return
        if not field.data.filename:
            raise validators.ValidationError(
                _("Incorrect filename.")
            )
        if len(field.data.filename) > ASSET_FILENAME_LENGTH:
            raise validators.ValidationError(
                _(
                    "Filename must be less than ${number} characters long.",
                    mapping={'number': ASSET_FILENAME_LENGTH,}
                )
            )
        if ASSET_FILENAME_RE.match(field.data.filename) is None:
            raise validators.ValidationError(
                _("Filename can only contain letters, numbers and symbols: _ - .")
            )
        if field.data.filename in self.disallow_filenames:
            raise validators.ValidationError(
                _("This filename is not allowed.")
            )
        if os.path.exists(os.path.join(self.assets_path, field.data.filename)):
            raise validators.ValidationError(
                _("File with this filename already exists on the server.")
            )
        if field.data.type not in self.ALLOWED_MIMETYPES:
            raise validators.ValidationError(
                _("Only PNG and JPG formats are allowed.")
            )
        file = field.data.file
        file.seek(0, os.SEEK_END)
        if file.tell() > 1024 * 512:
            raise validators.ValidationError(
                _("Maximal file size is restricted to 512 KB.")
            )
        file.seek(0)

    def get_filename(self):
        return self.new_file.data.filename

    def get_file(self):
        return self.new_file.data.file

class DeleteAssetForm(SecureForm):

    filename = fields.TextField(
        widget=widgets.HiddenInput(),
        validators=(
            validators.DataRequired(),
            validators.Length(max=ASSET_FILENAME_LENGTH),
            validators.Regexp(ASSET_FILENAME_RE),
        )
    )
