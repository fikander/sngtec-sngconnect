import decimal
import random
import string

import bcrypt
import sqlalchemy as sql
from sqlalchemy import orm
from sqlalchemy.ext.declarative import declarative_base
from zope.sqlalchemy import ZopeTransactionExtension

from sngconnect.translation import _

DBSession = orm.scoped_session(
    orm.sessionmaker(extension=ZopeTransactionExtension())
)

ModelBase = declarative_base()

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

    def set_password(self, new_password):
        self.password_hash = bcrypt.hashpw(new_password, bcrypt.gensalt())

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

class FeedTemplate(ModelBase):

    __tablename__ = 'sngconnect_feed_templates'

    id = sql.Column(
        sql.Integer,
        primary_key=True
    )

class Feed(ModelBase):

    __tablename__ = 'sngconnect_feeds'

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
    created = sql.Column(
        sql.DateTime(timezone=True),
        nullable=False
    )

    template = orm.relationship(
        FeedTemplate,
        backref=orm.backref('feeds'),
        lazy='joined'
    )

    def __repr__(self):
        return '<Feed(id=%s, name=\'%s\')>' % (self.id, self.name)

class DataStreamTemplate(ModelBase):

    __tablename__ = 'sngconnect_data_stream_templates'
    __table_args__ = (
        sql.UniqueConstraint('feed_template_id', 'label'),
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
        sql.Numeric(precision=50),
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
    def writeable(self):
        return self.template.writeable

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
            'MINIMAL_VALUE'
        ),
        nullable=False
    )
    boundary = sql.Column(
        sql.Numeric(precision=50),
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
    message_type = sql.Column(
        sql.Enum(
            'INFORMATION',
            'WARNING',
            'ERROR',
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

    def __repr__(self):
        return '<Message(id=%s)>' % self.id

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

    def __repr__(self):
        return ('<LogRequest(id=%s, feed_id=%s)>' %
            (
                self.id,
                self.feed_id,
            )
        )

    def regenerate_hash(self):
        self.hash = ''.join([
            random.choice(string.ascii_letters + string.digits)
            for n in xrange(50)
        ])

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
