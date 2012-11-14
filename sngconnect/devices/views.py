from sqlalchemy.orm import exc as database_exceptions
from pyramid.view import view_config
from pyramid import httpexceptions

from sngconnect.database import DBSession, FeedTemplate, DataStreamTemplate

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
    data_stream_templates = DBSession.query(DataStreamTemplate).filter(
        DataStreamTemplate.feed_template == feed_template
    ).order_by(DataStreamTemplate.name)
    return {
        'feed_template': {
            'id': feed_template.id,
            'name': feed_template.name,
            'url': request.route_url(
                'sngconnect.devices.feed_template',
                feed_template_id=feed_template.id
            ),
            'data_stream_templates': [
                {
                    'id': data_stream_template.id,
                    'name': data_stream_template.name,
                    'url': request.route_url(
                        'sngconnect.devices.data_stream_template',
                        feed_template_id=feed_template.id,
                        data_stream_template_id=data_stream_template.id
                    ),
                }
                for data_stream_template in data_stream_templates
            ],
        }
    }

@view_config(
    route_name='sngconnect.devices.data_stream_template',
    renderer='sngconnect.devices:templates/data_stream_template.jinja2',
    permission='sngconnect.devices.access'
)
def data_stream_template(request):
    try:
        feed_template, data_stream_template = DBSession.query(
            FeedTemplate,
            DataStreamTemplate
        ).filter(
            FeedTemplate.id == request.matchdict['feed_template_id'],
            (DataStreamTemplate.id ==
                request.matchdict['data_stream_template_id']),
            DataStreamTemplate.feed_template_id == FeedTemplate.id
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
        },
        'data_stream_template': {
            'id': data_stream_template.id,
            'name': data_stream_template.name,
            'url': request.route_url(
                'sngconnect.devices.data_stream_template',
                feed_template_id=feed_template.id,
                data_stream_template_id=data_stream_template.id
            ),
        },
    }
