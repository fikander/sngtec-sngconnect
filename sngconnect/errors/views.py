import urllib

from pyramid import httpexceptions
from pyramid.view import (view_config, notfound_view_config,
    forbidden_view_config)
from pyramid.response import Response

from sngconnect.translation import _

@view_config(
    context='pyramid.httpexceptions.HTTPBadRequest',
    renderer='sngconnect.errors:templates/bad_request.jinja2'
)
def error_bad_request(exception, request):
    if request.content_type == 'application/json':
        return Response(str(exception) + '\r\n', status=400)
    request.response.status = 400
    return {}

@forbidden_view_config()
def error_forbidden(exception, request):
    if request.content_type == 'application/json':
        return Response(status=403)
    request.session.flash(
        _(
            "You don't have permission to see this page."
            " Try logging in as a different user."
        ),
        queue='error'
    )
    return httpexceptions.HTTPSeeOther(
        '?'.join((
            request.route_url('sngconnect.accounts.sign_in'),
            'destination=%s' % urllib.quote_plus(request.path_qs)
        ))
    )

@notfound_view_config(
    renderer='sngconnect.errors:templates/not_found.jinja2'
)
def error_not_found(exception, request):
    if request.content_type == 'application/json':
        return Response(status=404)
    request.response.status = 404
    return {}
