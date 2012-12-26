import os
import errno
import datetime

from pyramid.view import view_config

from sngconnect.translation import _
from sngconnect.appearance import forms

@view_config(
    route_name='sngconnect.appearance.appearance',
    renderer='sngconnect.appearance:templates/appearance.jinja2',
    permission='sngconnect.appearance.access'
)
def appearance(request):
    assets_path = request.registry['settings'][
        'sngconnect.appearance_assets_upload_path'
    ]
    upload_form = forms.UploadAssetForm(
        assets_path,
        csrf_context=request
    )
    if request.method == 'POST':
        upload_form.process(request.POST)
        if upload_form.validate():
            filename = upload_form.get_filename()
            input_file = upload_form.get_file()
            output_file_path = os.path.join(assets_path, filename)
            try:
                os.makedirs(assets_path)
            except OSError as exception:
                if (exception.errno == errno.EEXIST and
                        os.path.isdir(assets_path)):
                    pass
                else:
                    raise
            with open(output_file_path, 'wb') as output_file:
                while True:
                    data = input_file.read(2 << 16)
                    if not data:
                        break
                    output_file.write(data)
            request.session.flash(
                _("New file has been succesfuly uploaded."),
                queue='success'
            )
        else:
            request.session.flash(
                _(
                    "There were some problems with your request."
                    " Please check the form for error messages."
                ),
                queue='error'
            )
    try:
        filenames = os.listdir(assets_path)
    except OSError:
        filenames = []
    files = []
    for filename in filenames:
        file_path = os.path.join(assets_path, filename)
        files.append({
            'filename': filename,
            'url': request.static_url(file_path),
            'size': int(os.path.getsize(file_path)),
            'last_modification': datetime.datetime.fromtimestamp(
                os.path.getmtime(file_path)
            ),
        })
    return {
        'files': files,
        'upload_form': upload_form,
    }
