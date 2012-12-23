from wtforms import fields, validators, widgets
from sqlalchemy.orm import exc as database_exceptions

from sngconnect.forms import SecureForm
from sngconnect.translation import _
from sngconnect.database import (DBSession, FeedTemplate, DataStreamTemplate,
    ChartDefinition)

class UpdateFeedTemplateForm(SecureForm):

    name = fields.TextField(
        _("Name"),
        validators=(
            validators.DataRequired(),
            validators.Length(max=200),
        )
    )

class AddFeedTemplateForm(UpdateFeedTemplateForm):

    def validate_name(self, field):
        if field.errors:
            return
        count = DBSession.query(FeedTemplate).filter(
            FeedTemplate.name == field.data
        ).count()
        if count > 0:
            raise validators.ValidationError(
                _("There is already device template having this name.")
            )

class DeleteFeedTemplateForm(SecureForm):

    feed_template_id = fields.IntegerField(
        widget=widgets.HiddenInput(),
        validators=(
            validators.DataRequired(),
        )
    )

    def __init__(self, feed_template_id=None, *args, **kwargs):
        self._feed_template_id = feed_template_id
        kwargs['feed_template_id'] = feed_template_id
        super(DeleteFeedTemplateForm, self).__init__(*args, **kwargs)

    def validate_feed_template_id(self, field):
        if field.data != self._feed_template_id:
            raise validators.ValidationError()

class UpdateDataStreamTemplateForm(SecureForm):

    feed_template_id = fields.IntegerField(
        widget=widgets.HiddenInput(),
        validators=(
            validators.DataRequired(),
        )
    )
    label = fields.TextField(
        _("Label"),
        validators=(
            validators.DataRequired(),
            validators.Length(max=100),
        )
    )
    name = fields.TextField(
        _("Name"),
        validators=(
            validators.DataRequired(),
            validators.Length(max=200),
        )
    )
    description = fields.TextAreaField(
        _("Description"),
        validators=(
            validators.Optional(),
            validators.Length(max=5000),
        )
    )
    measurement_unit = fields.TextField(
        _("Measurement unit"),
        validators=(
            validators.DataRequired(),
            validators.Length(max=50),
        )
    )
    writable = fields.BooleanField(
        _("Writable")
    )

    def __init__(self, feed_template_id=None, *args, **kwargs):
        self._feed_template_id = feed_template_id
        kwargs['feed_template_id'] = feed_template_id
        super(UpdateDataStreamTemplateForm, self).__init__(*args, **kwargs)

    def validate_feed_template_id(self, field):
        if field.data != self._feed_template_id:
            raise validators.ValidationError()

class AddDataStreamTemplateForm(UpdateDataStreamTemplateForm):

    def validate_label(self, field):
        if field.errors:
            return
        count = DBSession.query(DataStreamTemplate).filter(
            DataStreamTemplate.feed_template_id == self.feed_template_id.data,
            DataStreamTemplate.label == field.data
        ).count()
        if count > 0:
            raise validators.ValidationError(
                _("There is already parameter template having this label.")
            )

    def validate_name(self, field):
        if field.errors:
            return
        count = DBSession.query(DataStreamTemplate).filter(
            DataStreamTemplate.feed_template_id == self.feed_template_id.data,
            DataStreamTemplate.name == field.data
        ).count()
        if count > 0:
            raise validators.ValidationError(
                _("There is already parameter template having this name.")
            )

class DeleteDataStreamTemplateForm(SecureForm):

    data_stream_template_id = fields.IntegerField(
        widget=widgets.HiddenInput(),
        validators=(
            validators.DataRequired(),
        )
    )

    def __init__(self, data_stream_template_id=None, *args, **kwargs):
        self._data_stream_template_id = data_stream_template_id
        kwargs['data_stream_template_id'] = data_stream_template_id
        super(DeleteDataStreamTemplateForm, self).__init__(*args, **kwargs)

    def validate_data_stream_template_id(self, field):
        if field.data != self._data_stream_template_id:
            raise validators.ValidationError()

class AddChartDefinitionForm(SecureForm):

    chart_type = fields.SelectField(
        _("Type"),
        choices=[
            ('LINEAR', _("Linear")),
            ('DIFFERENTIAL', _("Differential")),
        ],
        validators=(
            validators.DataRequired(),
        )
    )
    name = fields.TextField(
        _("Name"),
        validators=(
            validators.DataRequired(),
            validators.Length(max=200),
        )
    )
    data_stream_template_ids = fields.SelectMultipleField(
        _("Select up to three parameters"),
        choices=[],
        coerce=int,
        validators=(
            validators.DataRequired(),
        )
    )

    def __init__(self, feed_template, data_stream_templates, *args, **kwargs):
        if 'obj' in kwargs:
            kwargs['data_stream_template_ids'] = [
                template.id for template in kwargs['obj'].data_stream_templates
            ]
        super(AddChartDefinitionForm, self).__init__(*args, **kwargs)
        self.feed_template = feed_template
        self.data_stream_template_ids.choices = [
            (template.id, template.name) for template in data_stream_templates
        ]

    def validate_name(self, field):
        if field.errors:
            return
        try:
            DBSession.query(ChartDefinition).filter(
                ChartDefinition.feed_template == self.feed_template,
                ChartDefinition.feed == None,
                ChartDefinition.name == field.data
            ).one()
        except database_exceptions.NoResultFound:
            pass
        else:
            raise validators.ValidationError(
                _("This chart name is already taken.")
            )

class UpdateChartDefinitionForm(AddChartDefinitionForm):

    id = fields.IntegerField(
        widget=widgets.HiddenInput(),
        validators=(
            validators.DataRequired(),
        )
    )

    def __init__(self, original_id, *args, **kwargs):
        self.original_id = original_id
        super(UpdateChartDefinitionForm, self).__init__(*args, **kwargs)

    def validate_id(self, field):
        if self.original_id != field.data:
            raise validators.ValidationError()

    def validate_name(self, field):
        if field.errors:
            return
        try:
            DBSession.query(ChartDefinition).filter(
                ChartDefinition.feed_template == self.feed_template,
                ChartDefinition.id != self.id.data,
                ChartDefinition.feed == None,
                ChartDefinition.name == field.data
            ).one()
        except database_exceptions.NoResultFound:
            pass
        else:
            raise validators.ValidationError(
                _("This chart name is already taken.")
            )

class DeleteChartDefinitionForm(SecureForm):

    chart_definition_id = fields.IntegerField(
        widget=widgets.HiddenInput(),
        validators=(
            validators.DataRequired(),
        )
    )

    def __init__(self, chart_definition_id=None, *args, **kwargs):
        self._chart_definition_id = chart_definition_id
        kwargs['chart_definition_id'] = chart_definition_id
        super(DeleteChartDefinitionForm, self).__init__(*args, **kwargs)

    def validate_chart_definition_id(self, field):
        if field.data != self._chart_definition_id:
            raise validators.ValidationError()
