from pyramid.view import view_config
from pyramid import httpexceptions

@view_config(
    route_name='sngconnect.telemetry.feeds',
    request_method='GET',
    permission='sngconnect.telemetry.access'
)
def feeds(request):
    return httpexceptions.HTTPSeeOther(
        request.route_url('sngconnect.telemetry.dashboard')
    )
