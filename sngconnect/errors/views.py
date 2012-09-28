from pyramid.view import view_config, notfound_view_config
from pyramid.response import Response

@view_config(
    context='pyramid.httpexceptions.HTTPBadRequest',
    renderer='sngconnect.errors:templates/bad_request.jinja2'
)
def error_bad_request(exception, request):
    if request.content_type == 'application/json':
        return Response(str(exception) + '\r\n', status=400)
    request.response.status = 400
    return {}

@notfound_view_config(
    renderer='sngconnect.errors:templates/not_found.jinja2'
)
def error_not_found(exception, request):
    if request.content_type == 'application/json':
        return Response(status=404)
    request.response.status = 404
    return {}
