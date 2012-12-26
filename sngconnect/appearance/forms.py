import os
import re

from wtforms import fields, validators

from sngconnect.forms import SecureForm
from sngconnect.translation import _

class UploadAssetForm(SecureForm):

    FILENAME_RE = re.compile(r'^[\w\-]+\.[\w\-]+$')

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
        self.assets_path = assets_path

    def validate_new_file(self, field):
        if field.errors or field.data == u'':
            return
        if not field.data.filename:
            raise validators.ValidationError(
                _("Incorrect filename.")
            )
        if len(field.data.filename) > 50:
            raise validators.ValidationError(
                _("Filename must be less than 50 characters long.")
            )
        if self.FILENAME_RE.match(field.data.filename) is None:
            raise validators.ValidationError(
                _("Filename can only contain letters, numbers and symbols: _ - .")
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
