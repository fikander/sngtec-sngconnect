import os

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
            validators.DataRequired(message=_("This field is required.")),
            validators.Length(max=200),
        )
    )
    modbus_bandwidth = fields.IntegerField(
        _("Modbus bandwidth"),
        validators=(
            validators.DataRequired(message=_("This field is required.")),
            validators.NumberRange(min=0),
        )
    )
    modbus_port = fields.TextField(
        _("Modbus port path"),
        validators=(
            validators.DataRequired(message=_("This field is required.")),
        )
    )
    modbus_parity = fields.SelectField(
        _("Modbus parity"),
        choices=[
            ('EVEN', _("Even")),
            ('ODD', _("Odd")),
        ],
        validators=(
            validators.DataRequired(message=_("This field is required.")),
        )
    )
    modbus_data_bits = fields.IntegerField(
        _("Modbus data bits"),
        validators=(
            validators.DataRequired(message=_("This field is required.")),
            validators.NumberRange(min=0),
        )
    )
    modbus_stop_bits = fields.IntegerField(
        _("Modbus stop bits"),
        validators=(
            validators.DataRequired(message=_("This field is required.")),
            validators.NumberRange(min=0),
        )
    )
    modbus_timeout = fields.IntegerField(
        _("Modbus timeout"),
        validators=(
            validators.DataRequired(message=_("This field is required.")),
            validators.NumberRange(min=0),
        )
    )
    modbus_endianness = fields.SelectField(
        _("Modbus endianness"),
        choices=[
            ('BIG', _("Big endian")),
            ('LITTLE', _("Little endian")),
        ],
        validators=(
            validators.DataRequired(message=_("This field is required.")),
        )
    )
    modbus_polling_interval = fields.IntegerField(
        _("Modbus polling interval"),
        validators=(
            validators.DataRequired(message=_("This field is required.")),
            validators.NumberRange(min=0),
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
            validators.DataRequired(message=_("This field is required.")),
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
            validators.DataRequired(message=_("This field is required.")),
        )
    )
    label = fields.TextField(
        _("Label"),
        validators=(
            validators.DataRequired(message=_("This field is required.")),
            validators.Length(max=100),
        )
    )
    name = fields.TextField(
        _("Name"),
        validators=(
            validators.DataRequired(message=_("This field is required.")),
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
            validators.DataRequired(message=_("This field is required.")),
            validators.Length(max=50),
        )
    )
    writable = fields.BooleanField(
        _("Writable")
    )
    modbus_register_type = fields.SelectField(
        _("Modbus register type"),
        choices=[
            ('HOLDING', _("Holding register")),
            ('INPUT', _("Input register")),
        ],
        validators=(
            validators.DataRequired(message=_("This field is required.")),
        )
    )
    modbus_slave = fields.IntegerField(
        _("Modbus slave"),
        validators=(
            validators.DataRequired(message=_("This field is required.")),
            validators.NumberRange(min=0),
        )
    )
    modbus_address = fields.IntegerField(
        _("Modbus address"),
        validators=(
            validators.DataRequired(message=_("This field is required.")),
            validators.NumberRange(min=0),
        )
    )
    modbus_count = fields.IntegerField(
        _("Modbus count"),
        validators=(
            validators.DataRequired(message=_("This field is required.")),
            validators.NumberRange(min=0),
        )
    )

    show_on_dashboard = fields.BooleanField(
        _("Show on dashboard")
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
            validators.DataRequired(message=_("This field is required.")),
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
            validators.DataRequired(message=_("This field is required.")),
        )
    )
    name = fields.TextField(
        _("Name"),
        validators=(
            validators.DataRequired(message=_("This field is required.")),
            validators.Length(max=200),
        )
    )
    data_stream_template_ids = fields.SelectMultipleField(
        _("Select up to three parameters"),
        choices=[],
        coerce=int,
        validators=(
            validators.DataRequired(message=_("This field is required.")),
        )
    )
    show_on_dashboard = fields.BooleanField(
        _("Show on dashboard")
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
            validators.DataRequired(message=_("This field is required.")),
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
            validators.DataRequired(message=_("This field is required.")),
        )
    )

    def __init__(self, chart_definition_id=None, *args, **kwargs):
        self._chart_definition_id = chart_definition_id
        kwargs['chart_definition_id'] = chart_definition_id
        super(DeleteChartDefinitionForm, self).__init__(*args, **kwargs)

    def validate_chart_definition_id(self, field):
        if field.data != self._chart_definition_id:
            raise validators.ValidationError()

class ChangeFeedTemplateImageForm(SecureForm):

    ALLOWED_MIMETYPES = (
        'image/png',
        'image/jpeg',
    )

    new_image = fields.FileField(
        _("Image file"),
        description=_("Only PNG and JPG formats are allowed. Leave empty to delete current image."),
    )

    def validate_new_image(self, field):
        if field.errors or field.data == u'':
            return
        if field.data.type not in self.ALLOWED_MIMETYPES:
            raise validators.ValidationError(
                _("Only PNG and JPG formats are allowed.")
            )
        file = field.data.file
        file.seek(0, os.SEEK_END)
        if file.tell() > 1024 * 512:
            raise validators.ValidationError(
                _("Maximal file size is restricted to 512 KB.")
            )
        file.seek(0)

    def get_file(self):
        return self.new_image.data.file
