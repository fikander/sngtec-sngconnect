from sqlalchemy.orm import exc as database_exceptions
from pyramid.view import view_config
from pyramid import httpexceptions

from sngconnect.translation import _
from sngconnect.database import (DBSession, FeedTemplate, DataStreamTemplate,
    Feed, DataStream, ChartDefinition)
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
            return httpexceptions.HTTPFound(
                request.route_url('sngconnect.devices.feed_templates')
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
                'delete_url': request.route_url(
                    'sngconnect.devices.feed_template_delete',
                    feed_template_id=feed_template.id
                ),
                'delete_form': forms.DeleteFeedTemplateForm(
                    csrf_context=request,
                    feed_template_id=feed_template.id
                ),
            }
            for feed_template in feed_templates
        ]
    }

@view_config(
    route_name='sngconnect.devices.feed_template_delete',
    request_method='POST',
    permission='sngconnect.devices.access'
)
def feed_template_delete(request):
    try:
        feed_template = DBSession.query(FeedTemplate).filter(
            FeedTemplate.id == request.matchdict['feed_template_id']
        ).one()
    except database_exceptions.NoResultFound:
        raise httpexceptions.HTTPNotFound()
    delete_form = forms.DeleteFeedTemplateForm(
        feed_template_id=feed_template.id,
        csrf_context=request
    )
    delete_form.process(request.POST)
    if delete_form.validate():
        dependent_feed_count = DBSession.query(Feed).filter(
            Feed.template == feed_template
        ).count()
        dependent_data_stream_template_count = DBSession.query(
            DataStreamTemplate
        ).filter(
            DataStreamTemplate.feed_template == feed_template
        ).count()
        if dependent_feed_count > 0:
            request.session.flash(
                _(
                    "Device template cannot be deleted as there are"
                    " already devices basing on it. Contact the system"
                    " support for further information."
                ),
                queue='error'
            )
        elif dependent_data_stream_template_count > 0:
            request.session.flash(
                _(
                    "Device template cannot be deleted as it has parameter"
                    " templates assigned to it. Contact the system support for"
                    " further information."
                ),
                queue='error'
            )
        else:
            DBSession.delete(feed_template)
            request.session.flash(
                _("Device template has been successfuly deleted."),
                queue='success'
            )
    else:
        request.session.flash(
            _(
                "There were some problems with your request."
                " Contact the system support."
            ),
            queue='error'
        )
    return httpexceptions.HTTPFound(
        request.route_url('sngconnect.devices.feed_templates')
    )

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
    feed_template_form = forms.UpdateFeedTemplateForm(
        obj=feed_template,
        csrf_context=request
    )
    data_stream_template_form = forms.AddDataStreamTemplateForm(
        feed_template_id=feed_template.id,
        csrf_context=request
    )
    chart_definition_form = forms.AddChartDefinitionForm(
        feed_template,
        data_stream_templates,
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
                return httpexceptions.HTTPFound(
                    request.route_url('sngconnect.devices.feed_template'),
                    feed_template_id=feed_template.id
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
                    _("Parameter template has been successfuly added."),
                    queue='success'
                )
                return httpexceptions.HTTPFound(
                    request.route_url(
                        'sngconnect.devices.feed_template',
                        feed_template_id=feed_template.id
                    )
                )
            else:
                request.session.flash(
                    _(
                        "There were some problems with your request."
                        " Please check the form for error messages."
                    ),
                    queue='error'
                )
        elif 'submit_add_chart_definition' in request.POST:
            chart_definition_form.process(request.POST)
            data_stream_templates_dict = dict((
                (template.id, template)
                for template in data_stream_templates
            ))
            if chart_definition_form.validate():
                chart_definition = ChartDefinition(
                    feed_template=feed_template
                )
                chart_definition_form.populate_obj(chart_definition)
                for id in chart_definition_form.data_stream_template_ids.data:
                    chart_definition.data_stream_templates.append(
                        data_stream_templates_dict[id]
                    )
                DBSession.add(chart_definition)
                request.session.flash(
                    _("Chart has been successfuly added."),
                    queue='success'
                )
                return httpexceptions.HTTPFound(
                    request.route_url(
                        'sngconnect.devices.feed_template',
                        feed_template_id=feed_template.id
                    )
                )
            else:
                request.session.flash(
                    _(
                        "There were some problems with your request."
                        " Please check the form for error messages."
                    ),
                    queue='error'
                )
    chart_definitions = DBSession.query(ChartDefinition).filter(
        ChartDefinition.feed_template == feed_template,
        ChartDefinition.feed == None
    ).order_by(ChartDefinition.name)
    return {
        'feed_template_form': feed_template_form,
        'data_stream_template_form': data_stream_template_form,
        'chart_definition_form': chart_definition_form,
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
                    'delete_url': request.route_url(
                        'sngconnect.devices.data_stream_template_delete',
                        feed_template_id=feed_template.id,
                        data_stream_template_id=data_stream_template.id
                    ),
                    'delete_form': forms.DeleteDataStreamTemplateForm(
                        csrf_context=request,
                        data_stream_template_id=data_stream_template.id
                    ),
                }
                for data_stream_template in data_stream_templates
            ],
            'chart_definitions': [
                {
                    'id': chart_definition.id,
                    'name': chart_definition.name,
                    'type_name': chart_definition.chart_type_name,
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
                        for data_stream_template
                        in chart_definition.data_stream_templates
                    ],
                    'url': request.route_url(
                        'sngconnect.devices.chart_definition',
                        feed_template_id=feed_template.id,
                        chart_definition_id=chart_definition.id
                    ),
                    'delete_url': request.route_url(
                        'sngconnect.devices.chart_definition_delete',
                        feed_template_id=feed_template.id,
                        chart_definition_id=chart_definition.id
                    ),
                    'delete_form': forms.DeleteChartDefinitionForm(
                        csrf_context=request,
                        chart_definition_id=chart_definition.id
                    ),
                }
                for chart_definition in chart_definitions
            ],
        }
    }

@view_config(
    route_name='sngconnect.devices.data_stream_template_delete',
    request_method='POST',
    permission='sngconnect.devices.access'
)
def data_stream_template_delete(request):
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
    delete_form = forms.DeleteDataStreamTemplateForm(
        data_stream_template_id=data_stream_template.id,
        csrf_context=request
    )
    delete_form.process(request.POST)
    if delete_form.validate():
        dependent_count = DBSession.query(DataStream).filter(
            DataStream.template == data_stream_template
        ).count()
        if dependent_count == 0:
            DBSession.delete(data_stream_template)
            request.session.flash(
                _("Parameter template has been successfuly deleted."),
                queue='success'
            )
        else:
            request.session.flash(
                _(
                    "Parameter template cannot be deleted as there are"
                    " already parameters basing on it. Contact the system"
                    " support for further information."
                ),
                queue='error'
            )
    else:
        request.session.flash(
            _(
                "There were some problems with your request."
                " Contact the system support."
            ),
            queue='error'
        )
    return httpexceptions.HTTPFound(
        request.route_url(
            'sngconnect.devices.feed_template',
            feed_template_id=feed_template.id
        )
    )

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
            return httpexceptions.HTTPFound(
                request.route_url(
                    'sngconnect.devices.data_stream_template',
                    feed_template_id=feed_template.id,
                    data_stream_template_id=data_stream_template.id
                )
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

@view_config(
    route_name='sngconnect.devices.chart_definition_delete',
    request_method='POST',
    permission='sngconnect.devices.access'
)
def chart_definition_delete(request):
    try:
        feed_template, chart_definition = DBSession.query(
            FeedTemplate,
            ChartDefinition
        ).filter(
            FeedTemplate.id == request.matchdict['feed_template_id'],
            (ChartDefinition.id ==
                request.matchdict['chart_definition_id']),
            ChartDefinition.feed_template_id == FeedTemplate.id,
            ChartDefinition.feed == None
        ).one()
    except database_exceptions.NoResultFound:
        raise httpexceptions.HTTPNotFound()
    delete_form = forms.DeleteChartDefinitionForm(
        chart_definition_id=chart_definition.id,
        csrf_context=request
    )
    delete_form.process(request.POST)
    if delete_form.validate():
        DBSession.delete(chart_definition)
        request.session.flash(
            _("Chart has been successfuly deleted."),
            queue='success'
        )
    else:
        request.session.flash(
            _(
                "There were some problems with your request."
                " Contact the system support."
            ),
            queue='error'
        )
    return httpexceptions.HTTPFound(
        request.route_url(
            'sngconnect.devices.feed_template',
            feed_template_id=feed_template.id
        )
    )

@view_config(
    route_name='sngconnect.devices.chart_definition',
    renderer='sngconnect.devices:templates/chart_definition.jinja2',
    permission='sngconnect.devices.access'
)
def chart_definition(request):
    try:
        feed_template, chart_definition = DBSession.query(
            FeedTemplate,
            ChartDefinition
        ).filter(
            FeedTemplate.id == request.matchdict['feed_template_id'],
            (ChartDefinition.id ==
                request.matchdict['chart_definition_id']),
            ChartDefinition.feed_template_id == FeedTemplate.id,
            ChartDefinition.feed == None
        ).one()
    except database_exceptions.NoResultFound:
        raise httpexceptions.HTTPNotFound()
    data_stream_templates = DBSession.query(DataStreamTemplate).filter(
        DataStreamTemplate.feed_template == feed_template
    ).order_by(DataStreamTemplate.name)
    chart_definition_form = forms.UpdateChartDefinitionForm(
        chart_definition.id,
        feed_template,
        data_stream_templates,
        obj=chart_definition,
        csrf_context=request
    )
    if request.method == 'POST':
        chart_definition_form.process(request.POST)
        data_stream_templates_dict = dict((
            (template.id, template)
            for template in data_stream_templates
        ))
        if chart_definition_form.validate():
            chart_definition_form.populate_obj(chart_definition)
            chart_definition.data_stream_templates = []
            for id in chart_definition_form.data_stream_template_ids.data:
                chart_definition.data_stream_templates.append(
                    data_stream_templates_dict[id]
                )
            DBSession.add(chart_definition)
            request.session.flash(
                _("Parameter template has been successfuly saved."),
                queue='success'
            )
            return httpexceptions.HTTPFound(
                request.route_url(
                    'sngconnect.devices.chart_definition',
                    feed_template_id=feed_template.id,
                    chart_definition_id=chart_definition.id
                )
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
        'chart_definition_form': chart_definition_form,
        'feed_template': {
            'id': feed_template.id,
            'name': feed_template.name,
            'url': request.route_url(
                'sngconnect.devices.feed_template',
                feed_template_id=feed_template.id
            ),
        },
        'chart_definition': {
            'id': chart_definition.id,
            'name': chart_definition.name,
            'url': request.route_url(
                'sngconnect.devices.chart_definition',
                feed_template_id=feed_template.id,
                chart_definition_id=chart_definition.id
            ),
        },
    }
