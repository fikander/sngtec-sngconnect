from sqlalchemy.orm import exc as database_exceptions
from pyramid.view import view_config
from pyramid import httpexceptions

from sngconnect.database import DBSession, FeedTemplate

@view_config(
    route_name='sngconnect.devices.feed_templates',
    renderer='sngconnect.devices:templates/feed_templates.jinja2',
    permission='sngconnect.devices.access'
)
def feed_templates(request):
    feed_templates = DBSession.query(FeedTemplate).order_by(
        FeedTemplate.name
    )
    return {
        'feed_templates': [
            {
                'id': feed_template.id,
                'name': feed_template.name,
                'url': request.route_url(
                    'sngconnect.devices.feed_template',
                    feed_template_id=feed_template.id
                ),
            }
            for feed_template in feed_templates
        ]
    }

@view_config(
    route_name='sngconnect.devices.feed_template',
    renderer='sngconnect.devices:templates/feed_template.jinja2',
    permission='sngconnect.devices.access'
)
def feed_template(request):
    try:
        feed_template = DBSession.query(FeedTemplate).filter(
            FeedTemplate.id == request.matchdict['feed_template_id']
        ).one()
    except database_exceptions.NoResultFound:
        raise httpexceptions.HTTPNotFound()
    return {
        'feed_template': {
            'id': feed_template.id,
            'name': feed_template.name,
            'url': request.route_url(
                'sngconnect.devices.feed_template',
                feed_template_id=feed_template.id
            ),
        }
    }
