# -*- coding: utf-8 -*-

import os
import datetime
import sys

import pytz
import transaction
import sqlalchemy
from pyramid.paster import get_appsettings, setup_logging

from sngconnect.database import DBSession
from sngconnect.database import User


def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri>\n'
          '(example: "%s development.ini")' % (cmd, cmd))
    sys.exit(1)


def main(argv=sys.argv):
    if len(argv) != 2:
        usage(argv)
    config_uri = argv[1]
    setup_logging(config_uri)
    settings = get_appsettings(config_uri)
    database_engine = sqlalchemy.engine_from_config(settings, 'database.')
    DBSession.configure(bind=database_engine)
    generate_data()


def generate_data():
    user = User(
        name='User',
        email='user@example.com',
        phone='+48123456789',
        activated=pytz.utc.localize(datetime.datetime.utcnow()),
        role_user=True,
        timezone_tzname='Europe/Warsaw'
    )
    user.set_password('user')
    kid = User(
        name='Kid',
        email='kid@example.com',
        phone='+48123456789',
        activated=pytz.utc.localize(datetime.datetime.utcnow()),
        role_user=True,
        timezone_tzname='Europe/Warsaw'
    )
    kid.set_password('kid')
    maintainer = User(
        name='Maintainer',
        email='maintainer@example.com',
        phone='+48123456789',
        activated=pytz.utc.localize(datetime.datetime.utcnow()),
        role_maintainer=True,
        timezone_tzname='Europe/Warsaw'
    )
    maintainer.set_password('maintainer')
    supplier = User(
        name='Supplier',
        email='supplier@example.com',
        phone='+48123456789',
        activated=pytz.utc.localize(datetime.datetime.utcnow()),
        role_supplier=True,
        timezone_tzname='Europe/Warsaw'
    )
    supplier.set_password('supplier')
    admin = User(
        name='Admin',
        email='admin@example.com',
        phone='+48123456789',
        activated=pytz.utc.localize(datetime.datetime.utcnow()),
        role_administrator=True,
        timezone_tzname='Europe/Warsaw'
    )
    admin.set_password('admin')
    DBSession.add_all([user, kid, maintainer, supplier, admin])
    transaction.commit()

if __name__ == '__main__':
    sys.exit(main())
