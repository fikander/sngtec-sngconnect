import decimal

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
        doc="Password used to sign in to the system; hashed using bcrypt."
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

class System(ModelBase):

    __tablename__ = 'sngconnect_systems'

    id = sql.Column(
        sql.Integer,
        primary_key=True
    )
    name = sql.Column(
        sql.Unicode(length=200),
        nullable=False,
        doc="Name identifying concrete instance of a system."
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

    def __repr__(self):
        return '<System(id=%s, name=\'%s\')>' % (self.id, self.name)

class Parameter(ModelBase):

    __tablename__ = 'sngconnect_parameters'

    id = sql.Column(
        sql.Integer,
        primary_key=True
    )
    system_id = sql.Column(
        sql.Integer,
        sql.ForeignKey(System.id),
        nullable=False,
        doc="Related system's identifier."
    )
    name = sql.Column(
        sql.Unicode(length=200),
        nullable=False,
        doc="Name identifying firmly one of related system's measurable"
            " parameters."
    )
    description = sql.Column(
        sql.UnicodeText
    )
    measurement_unit = sql.Column(
        sql.Unicode(length=50),
        nullable=False,
        doc="Unit of measurement in which parameter values are expressed."
    )
    writable = sql.Column(
        sql.Boolean,
        nullable=False,
        doc="Whether to allow setting the parameter from the application."
    )
    minimal_value = sql.Column(
        sql.Numeric(precision=20),
        doc="Minimal allowed value."
    )
    maximal_value = sql.Column(
        sql.Numeric(precision=20),
        doc="Maximal allowed value."
    )

    system = orm.relationship(
        System,
        backref=orm.backref('parameters')
    )

    def __repr__(self):
        return '<Parameter(id=%s, system_id=%s, name=\'%s\')>' % (
            self.id,
            self.system_id,
            self.name
        )

class AlarmDefinition(ModelBase):

    __tablename__ = 'sngconnect_alarm_definitions'
    __table_args__ = (
        sql.UniqueConstraint('parameter_id', 'alarm_type'),
    )

    id = sql.Column(
        sql.Integer,
        primary_key=True
    )
    parameter_id = sql.Column(
        sql.Integer,
        sql.ForeignKey(Parameter.id),
        nullable=False,
        doc="Related parameter's identifier."
    )
    alarm_type = sql.Column(
        sql.Enum(
            'MAXIMAL_VALUE',
            'MINIMAL_VALUE'
        ),
        nullable=False
    )
    boundary = sql.Column(
        sql.Numeric(precision=10, scale=6),
        nullable=False
    )

    parameter = orm.relationship(
        Parameter,
        backref=orm.backref('alarm_definitions')
    )

    def __repr__(self):
        return ('<AlarmDefinition(id=%s, parameter_id=%s, alarm_type=\'%s\')>' %
            (
                self.id,
                self.parameter_id,
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
