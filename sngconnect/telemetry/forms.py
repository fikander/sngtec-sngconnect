import decimal

import sqlalchemy as sql
from wtforms import Form, fields, validators, widgets
from sqlalchemy.orm import exc as database_exceptions
import babel.numbers

from sngconnect.forms import SecureForm
from sngconnect.translation import _
from sngconnect.database import DBSession, User, ChartDefinition

class LocalizedDecimalField(fields.DecimalField):

    def _value(self):
        if self.raw_data:
            return self.raw_data[0]
        elif self.data is not None:
            return babel.numbers.format_decimal(
                self.data,
                format='0.##################################################',
                locale=self.locale
            )
        else:
            return ''

    def process_formdata(self, valuelist):
        if valuelist:
            try:
                self.data = decimal.Decimal(
                    str(
                        babel.numbers.parse_decimal(
                            valuelist[0],
                            locale=self.locale
                        )
                    )
                )
            except babel.numbers.NumberFormatError:
                self.data = None
                raise ValueError(self.gettext('Not a valid decimal value'))

    def set_locale(self, locale):
        self.locale = locale

class ValueForm(SecureForm):

    value = LocalizedDecimalField(
        _("Value"),
        places=None,
        validators=(
            validators.DataRequired(),
        )
    )

    def __init__(self, *args, **kwargs):
        locale = kwargs.pop('locale')
        super(ValueForm, self).__init__(*args, **kwargs)
        self.value.set_locale(locale)

class ValueBoundsForm(SecureForm):

    minimum = LocalizedDecimalField(
        _("Minimum"),
        places=None,
        validators=(
            validators.Optional(),
        )
    )
    maximum = LocalizedDecimalField(
        _("Maximum"),
        places=None,
        validators=(
            validators.Optional(),
        )
    )

    def __init__(self, *args, **kwargs):
        locale = kwargs.pop('locale')
        super(ValueBoundsForm, self).__init__(*args, **kwargs)
        self.minimum.set_locale(locale)
        self.maximum.set_locale(locale)

    def validate_maximum(self, field):
        if field.errors:
            return
        if self.minimum.data > field.data:
            raise validators.ValidationError(
                _("Maximum must be greater than or equal to the minimum.")
            )

class AddFeedUserForm(SecureForm):

    email = fields.TextField(
        _("E-mail"),
        validators=(
            validators.DataRequired(),
            validators.Length(max=200),
            validators.Email(),
        )
    )

    def validate_email(self, field):
        if field.errors:
            return
        try:
            self.user = DBSession.query(User).filter(
                User.email == field.data,
                User.activated != None
            ).one()
        except database_exceptions.NoResultFound:
            raise validators.ValidationError(
                _("There is no active user having this e-mail address.")
            )

    def get_user(self):
        return self.user

class AddFeedMaintainerForm(AddFeedUserForm):
    pass

class CreateChartDefinitionForm(SecureForm):

    chart_type = fields.HiddenField(
        validators=(
            validators.DataRequired(),
            validators.AnyOf(('LINEAR', 'DIFFERENTIAL',)),
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

    def __init__(self, feed, data_stream_templates, *args, **kwargs):
        if 'obj' in kwargs:
            kwargs['data_stream_template_ids'] = [
                template.id for template in kwargs['obj'].data_stream_templates
            ]
        super(CreateChartDefinitionForm, self).__init__(*args, **kwargs)
        self.feed = feed
        self.data_stream_template_ids.choices = [
            (template.id, template.name) for template in data_stream_templates
        ]

    def validate_name(self, field):
        if field.errors:
            return
        try:
            DBSession.query(ChartDefinition).filter(
                ChartDefinition.feed_template == self.feed.template,
                sql.or_(
                    ChartDefinition.feed == None,
                    ChartDefinition.feed == self.feed
                ),
                ChartDefinition.name == field.data
            ).one()
        except database_exceptions.NoResultFound:
            pass
        else:
            raise validators.ValidationError(
                _("This chart name is already taken.")
            )

class UpdateChartDefinitionForm(CreateChartDefinitionForm):

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
                ChartDefinition.feed_template == self.feed.template,
                ChartDefinition.id != self.id.data,
                sql.or_(
                    ChartDefinition.feed == None,
                    ChartDefinition.feed == self.feed
                ),
                ChartDefinition.name == field.data
            ).one()
        except database_exceptions.NoResultFound:
            pass
        else:
            raise validators.ValidationError(
                _("This chart name is already taken.")
            )

class DeleteChartDefinitionForm(SecureForm):
    pass

class SetChartRangeForm(SecureForm):

    start = fields.DateField(
        validators=(
            validators.DataRequired(),
        )
    )
    end = fields.DateField(
        validators=(
            validators.DataRequired(),
        )
    )

    def validate_end(self, field):
        if field.errors:
            return
        if field.data <= self.start.data:
            raise validators.ValidationError(
                _("End date must be greater than start date.")
            )

class CommentForm(SecureForm):

    content = fields.TextAreaField(
        _("Content"),
        validators=(
            validators.DataRequired(),
            validators.Length(min=5, max=100000),
        )
    )

class FilterMessagesForm(Form):

    data_stream_template_id = fields.SelectField(
        _("Parameter"),
        choices=[],
        coerce=lambda x: None if x == '' else int(x)
    )
    author_id = fields.SelectField(
        _("Author"),
        choices=[],
        coerce=lambda x: None if x == '' else int(x)
    )

    def __init__(self, feed, users, data_stream_templates, message_service, *args, **kwargs):
        super(FilterMessagesForm, self).__init__(*args, **kwargs)
        self.feed = feed
        self.message_service = message_service
        self.data_stream_template_id.choices = [
            ('', _("All")),
            (-1, _("None")),
        ] + [
            (template.id, template.name) for template in data_stream_templates
        ]
        self.author_id.choices = [
            ('', _("All")),
        ] + [
            (user.id, user.email) for user in users
        ]

    def get_messages(self):
        return self.message_service.get_feed_messages(
            self.feed,
            data_stream_template_id=self.data_stream_template_id.data,
            author_id=self.author_id.data
        )

class CreateFeedForm(SecureForm):

    template_id = fields.SelectField(
        _("Device type"),
        choices=[],
        coerce=int
    )
    owner_email = fields.TextField(
        _("Owner's e-mail"),
        validators=(
            validators.DataRequired(),
            validators.Length(max=200),
            validators.Email(),
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
            validators.Length(max=1000),
        )
    )
    address = fields.TextField(
        _("Address"),
        validators=(
            validators.Length(max=200),
        )
    )
    latitude = LocalizedDecimalField(
        _("Latitude"),
        places=None
    )
    longitude = LocalizedDecimalField(
        _("Longitude"),
        places=None
    )

    def __init__(self, feed_templates, forced_owner, *args, **kwargs):
        if forced_owner is not None:
            kwargs['owner_email'] = forced_owner.email
            self.disable_owner_email = True
        else:
            self.disable_owner_email = False
        self.forced_owner = forced_owner
        super(CreateFeedForm, self).__init__(*args, **kwargs)
        self.template_id.choices = [
            (template.id, template.name) for template in feed_templates
        ]

    def validate_owner_email(self, field):
        if self.forced_owner is not None:
            if self.owner_email.data != self.forced_owner.email:
                raise validators.ValidationError("")
