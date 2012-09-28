from pyramid.view import view_config

@view_config(
    route_name='sngconnect.telemetry.dashboard',
    request_method='GET',
    renderer='sngconnect.telemetry:templates/dashboard.jinja2'
)
def dashboard(request):
    return {}
