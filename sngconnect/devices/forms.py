from wtforms import fields, validators, widgets

from sngconnect.forms import SecureForm
from sngconnect.translation import _
from sngconnect.database import DBSession, FeedTemplate, DataStreamTemplate

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
