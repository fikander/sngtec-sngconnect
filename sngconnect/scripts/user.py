# -*- coding: utf-8 -*-

import os
import datetime
import sys
from optparse import OptionParser

import pytz
import transaction
import sqlalchemy
from sqlalchemy.orm import exc as database_exceptions
from pyramid.paster import get_appsettings, setup_logging

from sngconnect.database import DBSession
from sngconnect.database import (User, FeedTemplate, Feed, DataStreamTemplate,
                                 DataStream, FeedUser)

MODES = ["add", "delete", "edit", "list"]


class CommandException(Exception):
    pass


def main(argv=sys.argv):

    usage =\
        "%prog ({0}) [options]\n"\
        "Example:\n"\
        "\t%prog add -n 'New User' -e 'email@example.com' -p '12345' "\
        "-r maintainer -t 'Europe/Warsaw'".format('|'.join(MODES))

    parser = OptionParser(usage)
    parser.add_option("-c", "--config", action="store",
                      help="You can also specify config with PYRAMID_CONFIG "
                           "environment variable")
    parser.add_option("-n", "--name", action="store")
    parser.add_option("-e", "--email", action="store")
    parser.add_option("", "--phone", action="store")
    parser.add_option("-r", "--role", action="append", dest="roles")
    parser.add_option("", "--tz", action="store", default="Europe/Warsaw",
                      metavar="TIMEZONE")
    parser.add_option("-p", "--password", action="store", default="password")

    (options, args) = parser.parse_args()

    if len(args) < 1:
        parser.error("No mode defined")

    if not options.config:
        options.config = os.environ.get('PYRAMID_CONFIG')
    if not options.config:
        parser.error("Specify Pyramid ini file with --config option "
                     "or PYRAMID_CONFIG environment variable")

    config_uri = options.config
    setup_logging(config_uri)
    settings = get_appsettings(config_uri)

    print("Using databases:")
    print("\tCassandra: %s" % settings["cassandra.keyspace"])
    print("\tDatabase : %s" % settings["database.url"])

    database_engine = sqlalchemy.engine_from_config(settings, 'database.')
    DBSession.configure(bind=database_engine)

    mode = args[0]
    if mode not in MODES:
        parser.error("Wrong mode")

    try:
        if mode == "list":
            list_users(options, settings)
        elif mode == "add":
            add_user(options, settings)
        elif mode == "edit":
            edit_user(options, settings)
        elif mode == "delete":
            delete_user(options, settings)
        else:
            raise Exception("Unimplemented mode")
    except Exception as e:
        parser.error(e)
        return 1

    return 0


def list_users(options, settings):
    users = DBSession.query(User).all()
    for user in users:
        d = {
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'phone': user.phone,
            'tokens': user.tokens,
            'tz': user.timezone_tzname,
            'last_payment': user.last_payment,
            'email_notifications': user.send_email_comment +
                                    (user.send_email_info << 1) +
                                    (user.send_email_warning << 2) +
                                    (user.send_email_error << 3),
            'sms_notifications': user.send_sms_comment +
                                    (user.send_sms_info << 1) +
                                    (user.send_sms_warning << 2) +
                                    (user.send_sms_error << 3),
        }
        print("{id:d}, {name} ({email}, {tz}), "
              "tokens:{tokens}, paid:{last_payment}, "
              "email:{email_notifications}, sms:{sms_notifications}".format(**d))


def add_user(options, settings):
    try:
        user = DBSession.query(User).filter(
            User.email == options.email
        ).one()
    except database_exceptions.NoResultFound:
        user = None
    if user:
        raise CommandException("This user already exists")
    if not options.roles:
        options.roles = []

    user = User(
        name=options.name,
        email=options.email,
        phone=options.phone,
        activated=pytz.utc.localize(datetime.datetime.utcnow()),
        role_user='user' in options.roles,
        role_supplier='supplier' in options.roles,
        role_administrator='administrator' in options.roles,
        role_maintainer='maintainer' in options.roles,
        timezone_tzname=options.tz
    )
    user.set_password(options.password)
    DBSession.add(user)
    transaction.commit()


def edit_user(options, settings):
    if not options.email:
        raise CommandException("Need email to find a user")
    try:
        user = DBSession.query(User).filter(
            User.email == options.email
        ).one()
    except database_exceptions.NoResultFound:
        raise CommandException(
            "User with email {0} doens't exist".format(options.email)
        )
    if options.name:
        user.name = options.name
    if options.phone:
        user.phone = options.phone
    if options.roles:
        user.role_user = 'user' in options.roles
        user.role_supplier = 'supplier' in options.roles
        user.role_administrator = 'administrator' in options.roles
        user.role_maintainer = 'maintainer' in options.roles
    if options.tz:
        user.timezone_tzname = options.tz
    DBSession.add(user)
    transaction.commit()


def delete_user(options, settings):
    if not options.email:
        raise CommandException("Need email to find a user")
    try:
        user = DBSession.query(User).filter(
            User.email == options.email
        ).one()
    except database_exceptions.NoResultFound:
        raise CommandException(
            "User with email {0} doens't exist".format(options.email)
        )
    DBSession.delete(user)
    transaction.commit()


if __name__ == '__main__':
    sys.exit(main())
