# -*- coding: utf-8 -*-

import os
import datetime
import sys

import pytz
import transaction
import sqlalchemy
from pyramid.paster import get_appsettings, setup_logging

from sngconnect.database import DBSession
from sngconnect.database import (User, FeedTemplate, Feed, DataStreamTemplate,
    DataStream, FeedUser)

def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri> <feed_count>\n'
          '(example: "%s development.ini 3")' % (cmd, cmd))
    sys.exit(1)

def main(argv=sys.argv):
    if len(argv) != 2:
        usage(argv)
    config_uri = argv[1]
    setup_logging(config_uri)
    settings = get_appsettings(config_uri)
    database_engine = sqlalchemy.engine_from_config(settings, 'database.')
    DBSession.configure(bind=database_engine)
    create_test_data()

def create_test_data():
    starting_id = 100000
    feed_template = FeedTemplate(
        id=starting_id,
        name=u"Licznik prądu",
    )
    feed = Feed(
        id=starting_id,
        template=feed_template,
        name=u"Licznik prądu w biurze Synergii",
        description=u"Licznik prądu w biurze Synergii w Warszawie",
        address=u"ul. Bysławska 82 lok. 312\n04-993 Warszawa",
        latitude=52.158427,
        longitude=21.198292,
        api_key='pnqt1tgDLBbzoghjCBDrpcD2NXUCP1WGFUDwm7baQTgmgueS5eU5c4W9EpLrnorJKC4DMfKe255YbwPvAJ7ppbD21NAs8XLk4XQb',
        created=pytz.utc.localize(datetime.datetime.utcnow())
    )
    user = DBSession.query(User).filter(User.email == 'user@example.com').one()
    feed_user = FeedUser(
        id=starting_id,
        feed=feed,
        user=user,
        role_user=True,
        can_change_permissions=True
    )
    DBSession.add_all([feed_template, feed, feed_user])
    data_stream_templates = [
        DataStreamTemplate(
            id=starting_id,
            feed_template=feed_template,
            label='t1_total',
            name='t1_total',
            measurement_unit='?',
            writable=False
        ),
        DataStreamTemplate(
            id=starting_id + 1,
            feed_template=feed_template,
            label='t2_total',
            name='t2_total',
            measurement_unit='?',
            writable=False
        ),
        DataStreamTemplate(
            id=starting_id + 2,
            feed_template=feed_template,
            label='baud',
            name='baud',
            measurement_unit='?',
            writable=False
        ),
        DataStreamTemplate(
            id=starting_id + 3,
            feed_template=feed_template,
            label='version',
            name='version',
            measurement_unit='?',
            writable=False
        ),
        DataStreamTemplate(
            id=starting_id + 4,
            feed_template=feed_template,
            label='phase1_URMS',
            name='phase1_URMS',
            measurement_unit='?',
            writable=False
        ),
        DataStreamTemplate(
            id=starting_id + 5,
            feed_template=feed_template,
            label='phase1_IRMS',
            name='phase1_IRMS',
            measurement_unit='?',
            writable=False
        ),
        DataStreamTemplate(
            id=starting_id + 6,
            feed_template=feed_template,
            label='phase1_PRMS',
            name='phase1_PRMS',
            measurement_unit='?',
            writable=False
        ),
        DataStreamTemplate(
            id=starting_id + 7,
            feed_template=feed_template,
            label='phase1_QRMS',
            name='phase1_QRMS',
            measurement_unit='?',
            writable=False
        ),
        DataStreamTemplate(
            id=starting_id + 8,
            feed_template=feed_template,
            label='phase1_cos_phi',
            name='phase1_cos_phi',
            measurement_unit='?',
            writable=False
        ),
        DataStreamTemplate(
            id=starting_id + 9,
            feed_template=feed_template,
            label='modbus_timeout',
            name='modbus_timeout',
            measurement_unit='?',
            writable=False
        ),
        DataStreamTemplate(
            id=starting_id + 10,
            feed_template=feed_template,
            label='total_PRMS',
            name='total_PRMS',
            measurement_unit='?',
            writable=False
        ),
        DataStreamTemplate(
            id=starting_id + 11,
            feed_template=feed_template,
            label='total_QRMS',
            name='total_QRMS',
            measurement_unit='?',
            writable=False
        ),
    ]
    DBSession.add_all(data_stream_templates)
    id = starting_id
    for data_stream_template in data_stream_templates:
        DBSession.add(
            DataStream(
                id=id,
                template=data_stream_template,
                feed=feed
            )
        )
        id += 1
    transaction.commit()
