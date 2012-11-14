from sqlalchemy.orm import exc as database_exceptions
from pyramid.view import view_config
from pyramid import httpexceptions

from sngconnect.translation import _
from sngconnect.database import DBSession, FeedTemplate, DataStreamTemplate
from sngconnect.devices import forms

@view_config(
    route_name='sngconnect.devices.feed_templates',
    renderer='sngconnect.devices:templates/feed_templates.jinja2',
    permission='sngconnect.devices.access'
)
def feed_templates(request):
    feed_template_form = forms.AddFeedTemplateForm(csrf_context=request)
    if request.method == 'POST':
        feed_template_form.process(request.POST)
        if feed_template_form.validate():
            feed_template = FeedTemplate()
            feed_template_form.populate_obj(feed_template)
            DBSession.add(feed_template)
            request.session.flash(
                _("Device template has been successfuly added."),
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
    feed_templates = DBSession.query(FeedTemplate).order_by(
        FeedTemplate.name
    )
    return {
        'feed_template_form': feed_template_form,
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
    feed_template_form = forms.UpdateFeedTemplateForm(
        obj=feed_template,
        csrf_context=request
    )
    data_stream_template_form = forms.AddDataStreamTemplateForm(
        feed_template_id=feed_template.id,
        csrf_context=request
    )
    if request.method == 'POST':
        if 'submit_save_feed_template' in request.POST:
            feed_template_form.process(request.POST)
            if feed_template_form.validate():
                feed_template_form.populate_obj(feed_template)
                DBSession.add(feed_template)
                request.session.flash(
                    _("Device template has been successfuly saved."),
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
        elif 'submit_add_data_stream_template' in request.POST:
            data_stream_template_form.process(request.POST)
            if data_stream_template_form.validate():
                data_stream_template = DataStreamTemplate()
                data_stream_template_form.populate_obj(data_stream_template)
                DBSession.add(data_stream_template)
                request.session.flash(
                    _("Parameter template has been successfuly saved."),
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
    data_stream_templates = DBSession.query(DataStreamTemplate).filter(
        DataStreamTemplate.feed_template == feed_template
    ).order_by(DataStreamTemplate.name)
    return {
        'feed_template_form': feed_template_form,
        'data_stream_template_form': data_stream_template_form,
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
                    'label': data_stream_template.label,
                    'writable': data_stream_template.writable,
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
    data_stream_template_form = forms.UpdateDataStreamTemplateForm(
        feed_template_id=feed_template.id,
        obj=data_stream_template,
        csrf_context=request
    )
    if request.method == 'POST':
        data_stream_template_form.process(request.POST)
        if data_stream_template_form.validate():
            data_stream_template_form.populate_obj(data_stream_template)
            DBSession.add(data_stream_template)
            request.session.flash(
                _("Parameter template has been successfuly saved."),
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
    return {
        'data_stream_template_form': data_stream_template_form,
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
