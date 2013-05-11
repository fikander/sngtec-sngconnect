import os
import decimal
import datetime
import random
import string

import pytz
import bcrypt
import sqlalchemy as sql
from sqlalchemy import orm
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import exc as database_exceptions
from zope.sqlalchemy import ZopeTransactionExtension

from sngconnect.translation import _
from sngconnect import security

DBSession = orm.scoped_session(
    orm.sessionmaker(extension=ZopeTransactionExtension())
)

ModelBase = declarative_base()

def generate_random_string(length):
    return ''.join([
        random.choice(string.ascii_letters + string.digits)
        for n in xrange(length)
    ])

class User(ModelBase):

    __tablename__ = 'sngconnect_users'

    id = sql.Column(
        sql.Integer,
        primary_key=True
    )
    email = sql.Column(
        sql.Unicode(length=200),
        nullable=False,
        index=True,
        doc="E-mail address used as a sign in credential and to send alerts"
            " and notifications."
    )
    password_hash = sql.Column(
        sql.String(length=100),
        nullable=False,
        doc="Password used to sign in to the feed; hashed using bcrypt."
    )
    phone = sql.Column(
        sql.String(length=50),
        doc="Phone number to send alerts and notifications to. `^\+\d+$`"
            " format."
    )

    name = sql.Column(
        sql.Unicode(length=200),
        nullable=False
    )
    company_name = sql.Column(
        sql.Unicode(length=200),
        nullable=True
    )

    activated = sql.Column(
        sql.DateTime(timezone=True),
        default=None
    )
    email_activation_code = sql.Column(
        sql.String(length=100),
        nullable=False
    )
    phone_activation_code = sql.Column(
        sql.String(length=30),
        nullable=False
    )

    tokens = sql.Column(
        sql.Integer,
        nullable=False,
        default=0
    )

    role_user = sql.Column(sql.Boolean, nullable=False, default=False)
    role_maintainer = sql.Column(sql.Boolean, nullable=False, default=False)
    role_supplier = sql.Column(sql.Boolean, nullable=False, default=False)
    role_administrator = sql.Column(sql.Boolean, nullable=False, default=False)

    send_email_error = sql.Column(sql.Boolean, nullable=False, default=True)
    send_email_warning = sql.Column(sql.Boolean, nullable=False, default=True)
    send_email_info = sql.Column(sql.Boolean, nullable=False, default=True)
    send_email_comment = sql.Column(sql.Boolean, nullable=False, default=False)

    send_sms_error = sql.Column(sql.Boolean, nullable=False, default=True)
    send_sms_warning = sql.Column(sql.Boolean, nullable=False, default=True)
    send_sms_info = sql.Column(sql.Boolean, nullable=False, default=True)
    send_sms_comment = sql.Column(sql.Boolean, nullable=False, default=False)

    timezone_tzname = sql.Column(sql.String(length=50), nullable=False)

    _role_mapping = {
        'role_user': security.User,
        'role_maintainer': security.Maintainer,
        'role_supplier': security.Supplier,
        'role_administrator': security.Administrator,
    }

    @property
    def roles(self):
        return [
            principal
            for attribute_name, principal in self._role_mapping.iteritems()
            if getattr(self, attribute_name, False)
        ]

    @property
    def timezone(self):
        return pytz.timezone(self.timezone_tzname)

    def __init__(self, *args, **kwargs):
        super(User, self).__init__(*args, **kwargs)
        if self.email_activation_code is None:
            self.regenerate_email_activation_code()
        if self.phone_activation_code is None:
            self.regenerate_phone_activation_code()

    def __setattr__(self, name, value):
        if name == 'email':
            value = value.lower()
        super(User, self).__setattr__(name, value)

    def set_password(self, new_password):
        self.password_hash = bcrypt.hashpw(new_password, bcrypt.gensalt())

    def regenerate_email_activation_code(self):
        self.email_activation_code = generate_random_string(40)

    def regenerate_phone_activation_code(self):
        self.phone_activation_code = generate_random_string(6).upper()

    def validate_password(self, password):
        """
        Returns `True` if given password is valid for this user and `False`
        otherwise.
        """
        return (
            bcrypt.hashpw(password, self.password_hash) == self.password_hash
        )

    def __repr__(self):
        return '<User(id=%s, email=\'%s\')>' % (self.id, self.email)

    @classmethod
    def authentication_callback(cls, user_id, request):
        try:
            user = DBSession.query(cls).filter(
                cls.id == user_id
            ).one()
        except database_exceptions.NoResultFound:
            return None
        return user.roles

class Order(ModelBase):

    __tablename__ = 'sngconnect_orders'

    id = sql.Column(
        sql.Integer,
        primary_key=True
    )
    status = sql.Column(
        sql.Enum(
            'PLACED',
            'CANCELED',
            'REALIZED',
            name='ORDER_STATUS_TYPE'
        ),
        nullable=False
    )
    placed = sql.Column(
        sql.DateTime,
        nullable=False
    )
    canceled = sql.Column(
        sql.DateTime
    )
    realized = sql.Column(
        sql.DateTime
    )
    user_id = sql.Column(
        sql.Integer,
        sql.ForeignKey(User.id),
        nullable=False
    )
    client_email = sql.Column(
        sql.Unicode(length=200),
        nullable=False
    )
    audit_data = sql.Column(
        sql.UnicodeText,
        nullable=False
    )
    tokens = sql.Column(
        sql.Integer,
        nullable=False
    )
    price_net = sql.Column(
        sql.Numeric(precision=14, scale=4),
        nullable=False
    )
    price_tax = sql.Column(
        sql.Numeric(precision=14, scale=4),
        nullable=False
    )
    price_gross = sql.Column(
        sql.Numeric(precision=14, scale=4),
        nullable=False
    )
    value_net = sql.Column(
        sql.Numeric(precision=14, scale=4),
        nullable=False
    )
    value_tax = sql.Column(
        sql.Numeric(precision=14, scale=4),
        nullable=False
    )
    value_gross = sql.Column(
        sql.Numeric(precision=14, scale=4),
        nullable=False
    )

    user = orm.relationship(
        User,
        backref=orm.backref('orders')
    )

class PayUSession(ModelBase):

    __tablename__ = 'sngconnect_payu_sessions'

    id = sql.Column(
        sql.Integer,
        primary_key=True
    )
    status = sql.Column(
        sql.Enum(
            'CREATED',
            'CANCELED',
            'REALIZED',
            name='PAYU_SESSION_STATUS_TYPE'
        ),
        nullable=False
    )
    order_id = sql.Column(
        sql.Integer,
        sql.ForeignKey(Order.id),
        nullable=False
    )
    create_order_request_id = sql.Column(
        sql.String(length=100),
        nullable=False
    )

    order = orm.relationship(
        Order,
        backref=orm.backref('payu_sessions')
    )

class FeedTemplate(ModelBase):

    __tablename__ = 'sngconnect_feed_templates'

    id = sql.Column(
        sql.Integer,
        primary_key=True
    )
    name = sql.Column(
        sql.Unicode(length=200),
        nullable=False,
        unique=True,
        doc="Name identifying template feed."
    )
    image = sql.Column(
        sql.String(length=50),
        nullable=True
    )

    modbus_bandwidth = sql.Column(
        sql.Integer,
        nullable=False
    )
    modbus_port = sql.Column(
        sql.String(length=50),
        nullable=False
    )
    modbus_parity = sql.Column(
        sql.Enum(
            'EVEN',
            'ODD',
            name='MODBUS_PARITY_TYPE'
        ),
        nullable=False
    )
    modbus_data_bits = sql.Column(
        sql.Integer,
        nullable=False
    )
    modbus_stop_bits = sql.Column(
        sql.Integer,
        nullable=False
    )
    modbus_timeout = sql.Column(
        sql.Integer,
        nullable=False
    )
    modbus_endianness = sql.Column(
        sql.Enum(
            'BIG',
            'LITTLE',
            name='MODBUS_ENDIANNESS_TYPE'
        ),
        nullable=False
    )
    modbus_polling_interval = sql.Column(
        sql.Integer,
        nullable=False
    )

    def get_image_path(self, request):
        if self.image is None:
            return None
        return os.path.join(
            request.registry['settings'][
                'sngconnect.device_image_upload_path'
            ],
            self.image[0],
            self.image[1],
            self.image
        )

    def get_image_url(self, request):
        path = self.get_image_path(request)
        if path is None:
            return None
        return request.static_url(path)

class Feed(ModelBase):

    __tablename__ = 'sngconnect_feeds'

    ACTIVATION_CODE_VALIDITY_PERIOD = datetime.timedelta(hours=12)

    id = sql.Column(
        sql.Integer,
        primary_key=True
    )
    template_id = sql.Column(
        sql.Integer,
        sql.ForeignKey(FeedTemplate.id),
        nullable=False,
        doc="Related template's identifier."
    )
    name = sql.Column(
        sql.Unicode(length=200),
        nullable=False,
        doc="Name identifying concrete instance of a feed."
    )
    description = sql.Column(
        sql.UnicodeText,
        doc="Instance description provided by the fixer."
    )
    address = sql.Column(
        sql.Unicode(length=200),
        doc="Instance address."
    )
    latitude = sql.Column(
        sql.Numeric(precision=10, scale=6),
        nullable=False
    )
    longitude = sql.Column(
        sql.Numeric(precision=10, scale=6),
        nullable=False
    )
    api_key = sql.Column(
        sql.String(length=100),
        nullable=False
    )
    created = sql.Column(
        sql.DateTime(timezone=True),
        nullable=False
    )
    activation_code = sql.Column(
        sql.String(length=50)
    )
    activation_code_regenerated = sql.Column(
        sql.DateTime(timezone=True)
    )
    device_uuid = sql.Column(
        sql.String(length=50)
    )

    template = orm.relationship(
        FeedTemplate,
        backref=orm.backref('feeds'),
        lazy='joined'
    )

    @property
    def template_name(self):
        return self.template.name

    def __init__(self, *args, **kwargs):
        super(Feed, self).__init__(*args, **kwargs)
        if self.api_key is None:
            self.regenerate_api_key()

    def __repr__(self):
        return '<Feed(id=%s, name=\'%s\')>' % (self.id, self.name)

    def regenerate_api_key(self):
        self.api_key = generate_random_string(100)

    def regenerate_activation_code(self):
        self.activation_code = generate_random_string(10).upper()
        self.activation_code_regenerated = pytz.utc.localize(
            datetime.datetime.utcnow()
        )

    def has_activation_code_expired(self):
        if self.activation_code_regenerated is None:
            return None
        difference = (
            pytz.utc.localize(datetime.datetime.utcnow()) -
            self.activation_code_regenerated
        )
        if difference > self.ACTIVATION_CODE_VALIDITY_PERIOD:
            return True
        else:
            return False

class FeedUser(ModelBase):

    __tablename__ = 'sngconnect_feed_users'
    __table_args__ = (
        sql.UniqueConstraint(
            'feed_id',
            'user_id',
            'role_user',
            'role_maintainer'
        ),
        sql.CheckConstraint('role_user <> role_maintainer'),
    )

    id = sql.Column(
        sql.Integer,
        primary_key=True
    )
    feed_id = sql.Column(
        sql.Integer,
        sql.ForeignKey(Feed.id),
        nullable=False
    )
    user_id = sql.Column(
        sql.Integer,
        sql.ForeignKey(User.id),
        nullable=False
    )

    role_user = sql.Column(
        sql.Boolean,
        nullable=False,
        default=False
    )
    role_maintainer = sql.Column(
        sql.Boolean,
        nullable=False,
        default=False
    )

    can_change_permissions = sql.Column(
        sql.Boolean,
        nullable=False,
        default=False
    )

    user = orm.relationship(
        User,
        backref=orm.backref('feed_users')
    )
    feed = orm.relationship(
        Feed,
        backref=orm.backref('feed_users')
    )

class DataStreamTemplate(ModelBase):

    __tablename__ = 'sngconnect_data_stream_templates'
    __table_args__ = (
        sql.UniqueConstraint('feed_template_id', 'label'),
        sql.UniqueConstraint('feed_template_id', 'name'),
    )

    id = sql.Column(
        sql.Integer,
        primary_key=True
    )
    feed_template_id = sql.Column(
        sql.Integer,
        sql.ForeignKey(FeedTemplate.id),
        nullable=False,
        doc="Related feed template's identifier."
    )
    label = sql.Column(
        sql.String(length=100),
        nullable=False,
        doc="Unique per feed label, used in URLs."
    )
    name = sql.Column(
        sql.Unicode(length=200),
        nullable=False,
        doc="Name identifying firmly one of related feed's measurable"
            " data_streams."
    )
    description = sql.Column(
        sql.UnicodeText
    )
    measurement_unit = sql.Column(
        sql.Unicode(length=50),
        nullable=False,
        doc="Unit of measurement in which data_stream values are expressed."
    )
    writable = sql.Column(
        sql.Boolean,
        nullable=False,
        doc="Whether to allow setting the data_stream from the application."
    )
    show_on_dashboard = sql.Column(
        sql.Boolean,
        nullable=False,
        default=False
    )

    default_minimum = sql.Column(
        sql.Numeric(precision=50, scale=25)
    )
    default_maximum = sql.Column(
        sql.Numeric(precision=50, scale=25)
    )

    modbus_register_type = sql.Column(
        sql.Enum(
            'HOLDING',
            'INPUT',
            name='MODBUS_REGISTER_TYPE'
        ),
        nullable=False
    )
    modbus_slave = sql.Column(
        sql.Integer,
        nullable=False
    )
    modbus_address = sql.Column(
        sql.Integer,
        nullable=False
    )
    modbus_count = sql.Column(
        sql.Integer,
        nullable=False
    )

    feed_template = orm.relationship(
        FeedTemplate,
        backref=orm.backref('data_stream_templates')
    )

class DataStream(ModelBase):

    __tablename__ = 'sngconnect_data_streams'

    id = sql.Column(
        sql.Integer,
        primary_key=True
    )
    template_id = sql.Column(
        sql.Integer,
        sql.ForeignKey(DataStreamTemplate.id),
        nullable=False,
        doc="Related template's identifier."
    )
    feed_id = sql.Column(
        sql.Integer,
        sql.ForeignKey(Feed.id),
        nullable=False,
        doc="Related feed's identifier."
    )
    requested_value = sql.Column(
        sql.Numeric(precision=50, scale=25),
        doc="Value requested by user."
    )
    value_requested_at = sql.Column(
        sql.DateTime(timezone=True),
        doc="Time the `requested_value` was set at."
    )

    template = orm.relationship(
        DataStreamTemplate,
        backref=orm.backref('data_streams'),
        lazy='joined'
    )
    feed = orm.relationship(
        Feed,
        backref=orm.backref('data_streams')
    )

    def __repr__(self):
        return '<DataStream(id=%s, feed_id=%s, name=\'%s\')>' % (
            self.id,
            self.feed_id,
            self.name
        )

    @property
    def label(self):
        return self.template.label

    @property
    def name(self):
        return self.template.name

    @property
    def description(self):
        return self.template.description

    @property
    def measurement_unit(self):
        return self.template.measurement_unit

    @property
    def writable(self):
        return self.template.writable

chart_definitions_data_stream_templates = sql.Table(
    'sngconnect_chart_definitions_data_stream_templates',
    ModelBase.metadata,
    sql.Column(
        'chart_definition_id',
        sql.Integer,
        sql.ForeignKey('sngconnect_chart_definitions.id')
    ),
    sql.Column(
        'data_stream_template_id',
        sql.Integer,
        sql.ForeignKey('sngconnect_data_stream_templates.id')
    ),
    sql.PrimaryKeyConstraint(
        'chart_definition_id',
        'data_stream_template_id'
    )
)

class ChartDefinition(ModelBase):

    __tablename__ = 'sngconnect_chart_definitions'
    __table_args__ = (
        sql.UniqueConstraint('feed_template_id', 'feed_id', 'name'),
    )

    id = sql.Column(
        sql.Integer,
        primary_key=True
    )
    feed_template_id = sql.Column(
        sql.Integer,
        sql.ForeignKey(FeedTemplate.id),
        nullable=False,
        doc="Related feed template's identifier."
    )
    feed_id = sql.Column(
        sql.Integer,
        sql.ForeignKey(Feed.id),
        doc="Related feed's identifier."
    )
    name = sql.Column(
        sql.Unicode(length=200),
        nullable=False
    )
    chart_type = sql.Column(
        sql.Enum(
            'LINEAR',
            'DIFFERENTIAL',
            name='CHART_DEFINITION_TYPE'
        ),
        nullable=False
    )
    show_on_dashboard = sql.Column(
        sql.Boolean,
        nullable=False,
        default=False
    )

    feed_template = orm.relationship(
        FeedTemplate,
        backref=orm.backref('chart_definitions')
    )
    feed = orm.relationship(
        Feed,
        backref=orm.backref('chart_definitions')
    )
    data_stream_templates = orm.relationship(
        DataStreamTemplate,
        secondary=chart_definitions_data_stream_templates,
        backref=orm.backref('chart_definitions')
    )

    @property
    def chart_type_name(self):
        if self.chart_type == 'LINEAR':
            return _("Linear")
        elif self.chart_type == 'DIFFERENTIAL':
            return _("Differential")
        else:
            return None

    @property
    def description(self):
        if self.chart_type == 'LINEAR':
            base = u"%s: " % _("Linear")
        elif self.chart_type == 'DIFFERENTIAL':
            base = u"%s: " % _("Differential")
        else:
            base = u""
        return base + u", ".join((
            template.name for template in self.data_stream_templates
        ))

    def __repr__(self):
        return '<ChartDefinition(id=%s)>' % str(self.id)

class AlarmDefinition(ModelBase):

    __tablename__ = 'sngconnect_alarm_definitions'
    __table_args__ = (
        sql.UniqueConstraint('data_stream_id', 'alarm_type'),
    )

    id = sql.Column(
        sql.Integer,
        primary_key=True
    )
    data_stream_id = sql.Column(
        sql.Integer,
        sql.ForeignKey(DataStream.id),
        nullable=False,
        doc="Related data_stream's identifier."
    )
    alarm_type = sql.Column(
        sql.Enum(
            'MAXIMAL_VALUE',
            'MINIMAL_VALUE',
            name='ALARM_DEFINITION_TYPE'
        ),
        nullable=False
    )
    boundary = sql.Column(
        sql.Numeric(precision=50, scale=25),
        nullable=False
    )

    data_stream = orm.relationship(
        DataStream,
        backref=orm.backref('alarm_definitions')
    )

    def __repr__(self):
        return (
            '<AlarmDefinition(id=%s, data_stream_id=%s, alarm_type=\'%s\')>' %
                (
                    self.id,
                    self.data_stream_id,
                    self.alarm_type
                )
        )

    def check_value(self, value):
        if isinstance(value, basestring):
            value = decimal.Decimal(value)
        if self.alarm_type == 'MAXIMAL_VALUE':
            if value > self.boundary:
                return _(
                    "Value (${actual_value}) is greater than maximal value"
                    " (${maximal_value}).",
                    mapping={
                        'actual_value': value,
                        'maximal_value': self.boundary,
                    }
                )
        elif self.alarm_type == 'MINIMAL_VALUE':
            if value < self.boundary:
                return _(
                    "Value (${actual_value}) is less than minimal value"
                    " (${minimal_value}).",
                    mapping={
                        'actual_value': value,
                        'minimal_value': self.boundary,
                    }
                )
        else:
            raise RuntimeError("Unknown alarm type.")
        return None

class Message(ModelBase):

    __tablename__ = 'sngconnect_messages'

    id = sql.Column(
        sql.Integer,
        primary_key=True
    )
    feed_id = sql.Column(
        sql.Integer,
        sql.ForeignKey(Feed.id),
        doc="Related feed's identifier."
    )
    data_stream_id = sql.Column(
        sql.Integer,
        sql.ForeignKey(DataStream.id),
        doc="Related data stream's identifier."
    )
    author_id = sql.Column(
        sql.Integer,
        sql.ForeignKey(User.id),
        doc="Author's identifier."
    )
    message_type = sql.Column(
        sql.Enum(
            'INFORMATION',
            'WARNING',
            'ERROR',
            'COMMENT',
            'ANNOUNCEMENT',
            name='MESSAGE_TYPE_TYPE'
        ),
        nullable=False
    )
    date = sql.Column(
        sql.DateTime(timezone=True),
        nullable=False
    )
    content = sql.Column(
        sql.UnicodeText,
        nullable=False
    )

    feed = orm.relationship(
        Feed,
        backref=orm.backref('messages')
    )
    data_stream = orm.relationship(
        DataStream,
        backref=orm.backref('messages')
    )
    author = orm.relationship(
        User,
        backref=orm.backref('authored_messages')
    )

    def __repr__(self):
        return '<Message(id=%s)>' % self.id

    @property
    def send_notifications(self):
        if self.message_type in ('ERROR', 'WARNING',):
            return True
        else:
            return False

    @property
    def confirmation_required(self):
        if self.message_type in ('ERROR',):
            return True
        else:
            return False

class LogRequest(ModelBase):

    __tablename__ = 'sngconnect_log_requests'

    id = sql.Column(
        sql.Integer,
        primary_key=True
    )
    feed_id = sql.Column(
        sql.Integer,
        sql.ForeignKey(Feed.id),
        nullable=False,
        doc="Related feed's identifier."
    )
    hash = sql.Column(
        sql.String(length=100),
        nullable=False
    )
    period_start = sql.Column(
        sql.DateTime(timezone=True),
        nullable=False
    )
    period_end = sql.Column(
        sql.DateTime(timezone=True),
        nullable=False
    )
    log = sql.Column(
        sql.UnicodeText
    )

    feed = orm.relationship(
        Feed,
        backref=orm.backref('log_requests')
    )

    def __init__(self, *args, **kwargs):
        super(LogRequest, self).__init__(*args, **kwargs)
        if self.hash is None:
            self.regenerate_hash()

    def __repr__(self):
        return ('<LogRequest(id=%s, feed_id=%s)>' %
            (
                self.id,
                self.feed_id,
            )
        )

    def regenerate_hash(self):
        self.hash = generate_random_string(50)

class Command(ModelBase):

    __tablename__ = 'sngconnect_commands'

    id = sql.Column(
        sql.Integer,
        primary_key=True
    )
    feed_id = sql.Column(
        sql.Integer,
        sql.ForeignKey(Feed.id),
        nullable=False,
        doc="Related feed's identifier."
    )
    command = sql.Column(
        sql.Enum(
            'reboot',
            'upload_log',
            name='COMMAND_TYPE'
        ),
        nullable=False
    )
    date = sql.Column(
        sql.DateTime(timezone=True),
        nullable=False
    )
    arguments = sql.Column(
        sql.PickleType(),
        nullable=False,
        default={}
    )

    feed = orm.relationship(
        Feed,
        backref=orm.backref('commands')
    )

    def __repr__(self):
        return '<Command(id=%s, command=\'%s\')>' % (
            self.id,
            self.command,
        )
