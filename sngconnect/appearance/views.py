import os
import errno
import datetime

from pyramid import httpexceptions
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
    stylesheet_filename = request.registry['settings'][
        'sngconnect.appearance_stylesheet_filename'
    ]
    stylesheet_file_path = os.path.join(assets_path, stylesheet_filename)
    stylesheet = None
    try:
        with open(stylesheet_file_path, 'r') as stylesheet_file:
            stylesheet = stylesheet_file.read()
    except IOError:
        pass
    update_stylesheet_form = forms.UpdateStylesheetForm(
        stylesheet=stylesheet,
        csrf_context=request
    )
    upload_form = forms.UploadAssetForm(
        assets_path,
        disallow_filenames=(
            stylesheet_filename,
        ),
        csrf_context=request
    )
    if request.method == 'POST':
        if 'submit_update_stylesheet' in request.POST:
            update_stylesheet_form.process(request.POST)
            if update_stylesheet_form.validate():
                with open(stylesheet_file_path, 'w') as output_file:
                    output_file.write(update_stylesheet_form.stylesheet.data)
                request.session.flash(
                    _("Stylesheet has been succesfuly saved."),
                    queue='success'
                )
                return httpexceptions.HTTPFound(
                    request.route_url('sngconnect.appearance.appearance')
                )
            else:
                request.session.flash(
                    _(
                        "There were some problems with your request."
                        " Please check the form for error messages."
                    ),
                    queue='error'
                )
        elif 'submit_upload_asset' in request.POST:
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
                return httpexceptions.HTTPFound(
                    request.route_url('sngconnect.appearance.appearance')
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
        filenames = set(os.listdir(assets_path))
    except OSError:
        filenames = set()
    filenames.discard(stylesheet_filename)
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
            'delete_url': request.route_url(
                'sngconnect.appearance.delete_asset'
            ),
            'delete_form': forms.DeleteAssetForm(
                filename=filename,
                csrf_context=request
            ),
        })
    return {
        'files': files,
        'update_stylesheet_form': update_stylesheet_form,
        'upload_form': upload_form,
    }

@view_config(
    route_name='sngconnect.appearance.delete_asset',
    request_method='POST',
    permission='sngconnect.appearance.access'
)
def delete_asset(request):
    assets_path = request.registry['settings'][
        'sngconnect.appearance_assets_upload_path'
    ]
    stylesheet_filename = request.registry['settings'][
        'sngconnect.appearance_stylesheet_filename'
    ]
    delete_form = forms.DeleteAssetForm(csrf_context=request)
    delete_form.process(request.POST)
    if delete_form.validate():
        if delete_form.filename.data != stylesheet_filename:
            try:
                os.remove(os.path.join(assets_path, delete_form.filename.data))
            except OSError:
                pass
        request.session.flash(
            _("File has been succesfuly deleted."),
            queue='success'
        )
        return httpexceptions.HTTPFound(
            request.route_url('sngconnect.appearance.appearance')
        )
    else:
        raise httpexceptions.HTTPBadRequest()
