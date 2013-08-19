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
    create_test_data()
    create_test_data2()


def create_test_data():
    starting_id = 100000
    feed_template = FeedTemplate(
        id=starting_id,
        name=u"Licznik prądu",
        dashboard_layout="GAUGES",
        modbus_bandwidth=9600,
        modbus_port='/dev/ttyS0',
        modbus_parity='EVEN',
        modbus_data_bits=8,
        modbus_stop_bits=1,
        modbus_timeout=5,
        modbus_endianness='BIG',
        modbus_polling_interval=120
    )
    feed = Feed(
        id=starting_id,
        template=feed_template,
        name=u"Licznik energii Saia-Burgess ALE3",
        description=u"Licznik prądu w biurze Synergii w Warszawie",
        address=u"ul. Bysławska 82 lok. 312\n04-993 Warszawa",
        latitude=52.158427,
        longitude=21.198292,
        api_key='pnqt1tgDLBbzoghjCBDrpcD2NXUCP1WGFUDwm7baQTgmgueS5eU5c4W9EpLrnorJKC4DMfKe255YbwPvAJ7ppbD21NAs8XLk4XQb',
        created=pytz.utc.localize(datetime.datetime.utcnow())
    )
    feed.regenerate_activation_code()
    user = DBSession.query(User).filter(User.email == 'user@example.com').one()
    feed_user = FeedUser(
        id=starting_id,
        feed=feed,
        user=user,
        role='OWNER_PLUS'
    )
    DBSession.add_all([feed_template, feed, feed_user])
    data_stream_templates = [
        DataStreamTemplate(
            id=starting_id,
            feed_template=feed_template,
            label='t1_total',
            name='t1_total',
            measurement_unit='0.01 kWh',
            writable=False,
            modbus_register_type='HOLDING',
            modbus_slave=1,
            modbus_address=27,
            modbus_count=2,
            show_on_dashboard=True,
            default_minimum=0,
            default_maximum=100,
        ),
        DataStreamTemplate(
            id=starting_id + 1,
            feed_template=feed_template,
            label='t2_total',
            name='t2_total',
            measurement_unit='0.01 kWh',
            writable=False,
            modbus_register_type='HOLDING',
            modbus_slave=1,
            modbus_address=31,
            modbus_count=2,
            show_on_dashboard=True,
            default_minimum=0,
            default_maximum=100,
        ),
        DataStreamTemplate(
            id=starting_id + 2,
            feed_template=feed_template,
            label='baud',
            name='baud',
            measurement_unit='baud',
            writable=False,
            modbus_register_type='HOLDING',
            modbus_slave=1,
            modbus_address=2,
            modbus_count=2
        ),
        DataStreamTemplate(
            id=starting_id + 3,
            feed_template=feed_template,
            label='version',
            name='version',
            measurement_unit='.',
            writable=False,
            modbus_register_type='HOLDING',
            modbus_slave=1,
            modbus_address=0,
            modbus_count=1
        ),
        DataStreamTemplate(
            id=starting_id + 4,
            feed_template=feed_template,
            label='phase1_URMS',
            name='phase1_URMS',
            measurement_unit='V',
            writable=False,
            modbus_register_type='HOLDING',
            modbus_slave=1,
            modbus_address=35,
            modbus_count=1
        ),
        DataStreamTemplate(
            id=starting_id + 5,
            feed_template=feed_template,
            label='phase1_IRMS',
            name='phase1_IRMS',
            measurement_unit='0.1 A',
            writable=False,
            modbus_register_type='HOLDING',
            modbus_slave=1,
            modbus_address=36,
            modbus_count=1
        ),
        DataStreamTemplate(
            id=starting_id + 6,
            feed_template=feed_template,
            label='phase1_PRMS',
            name='phase1_PRMS',
            measurement_unit='0.01 kW',
            writable=False,
            modbus_register_type='HOLDING',
            modbus_slave=1,
            modbus_address=37,
            modbus_count=1,
            show_on_dashboard=True,
            default_minimum=0,
            default_maximum=100,
        ),
        DataStreamTemplate(
            id=starting_id + 7,
            feed_template=feed_template,
            label='phase1_QRMS',
            name='phase1_QRMS',
            measurement_unit='0.01 kVA',
            writable=False,
            modbus_register_type='HOLDING',
            modbus_slave=1,
            modbus_address=38,
            modbus_count=1
        ),
        DataStreamTemplate(
            id=starting_id + 8,
            feed_template=feed_template,
            label='phase1_cos_phi',
            name='phase1_cos_phi',
            measurement_unit='.',
            writable=False,
            modbus_register_type='HOLDING',
            modbus_slave=1,
            modbus_address=39,
            modbus_count=1
        ),
        DataStreamTemplate(
            id=starting_id + 9,
            feed_template=feed_template,
            label='modbus_timeout',
            name='modbus_timeout',
            measurement_unit='s',
            writable=False,
            modbus_register_type='HOLDING',
            modbus_slave=1,
            modbus_address=22,
            modbus_count=1
        ),
        DataStreamTemplate(
            id=starting_id + 10,
            feed_template=feed_template,
            label='total_PRMS',
            name='total_PRMS',
            measurement_unit='0.01 kW',
            writable=False,
            modbus_register_type='HOLDING',
            modbus_slave=1,
            modbus_address=50,
            modbus_count=1,
            show_on_dashboard=True,
            default_minimum=0,
            default_maximum=100,
        ),
        DataStreamTemplate(
            id=starting_id + 11,
            feed_template=feed_template,
            label='total_QRMS',
            name='total_QRMS',
            measurement_unit='0.01 kVA',
            writable=False,
            modbus_register_type='HOLDING',
            modbus_slave=1,
            modbus_address=51,
            modbus_count=1
        ),
        DataStreamTemplate(
            id=starting_id + 12,
            feed_template=feed_template,
            label='phase2_URMS',
            name='phase2_URMS',
            measurement_unit='V',
            writable=False,
            modbus_register_type='HOLDING',
            modbus_slave=1,
            modbus_address=40,
            modbus_count=1
        ),
        DataStreamTemplate(
            id=starting_id + 13,
            feed_template=feed_template,
            label='phase2_IRMS',
            name='phase2_IRMS',
            measurement_unit='0.1 A',
            writable=False,
            modbus_register_type='HOLDING',
            modbus_slave=1,
            modbus_address=41,
            modbus_count=1
        ),
        DataStreamTemplate(
            id=starting_id + 14,
            feed_template=feed_template,
            label='phase2_PRMS',
            name='phase2_PRMS',
            measurement_unit='0.01 kW',
            writable=False,
            modbus_register_type='HOLDING',
            modbus_slave=1,
            modbus_address=42,
            modbus_count=1,
            show_on_dashboard=True,
            default_minimum=0,
            default_maximum=100,
        ),
        DataStreamTemplate(
            id=starting_id + 15,
            feed_template=feed_template,
            label='phase2_QRMS',
            name='phase2_QRMS',
            measurement_unit='0.01 kVA',
            writable=False,
            modbus_register_type='HOLDING',
            modbus_slave=1,
            modbus_address=43,
            modbus_count=1
        ),
        DataStreamTemplate(
            id=starting_id + 16,
            feed_template=feed_template,
            label='phase2_cos_phi',
            name='phase2_cos_phi',
            measurement_unit='.',
            writable=False,
            modbus_register_type='HOLDING',
            modbus_slave=1,
            modbus_address=44,
            modbus_count=1
        ),
        DataStreamTemplate(
            id=starting_id + 17,
            feed_template=feed_template,
            label='phase3_URMS',
            name='phase3_URMS',
            measurement_unit='V',
            writable=False,
            modbus_register_type='HOLDING',
            modbus_slave=1,
            modbus_address=45,
            modbus_count=1
        ),
        DataStreamTemplate(
            id=starting_id + 18,
            feed_template=feed_template,
            label='phase3_IRMS',
            name='phase3_IRMS',
            measurement_unit='0.1 A',
            writable=False,
            modbus_register_type='HOLDING',
            modbus_slave=1,
            modbus_address=46,
            modbus_count=1
        ),
        DataStreamTemplate(
            id=starting_id + 19,
            feed_template=feed_template,
            label='phase3_PRMS',
            name='phase3_PRMS',
            measurement_unit='0.01 kW',
            writable=False,
            modbus_register_type='HOLDING',
            modbus_slave=1,
            modbus_address=47,
            modbus_count=1,
            show_on_dashboard=True,
            default_minimum=0,
            default_maximum=100,
        ),
        DataStreamTemplate(
            id=starting_id + 20,
            feed_template=feed_template,
            label='phase3_QRMS',
            name='phase3_QRMS',
            measurement_unit='0.01 kVA',
            writable=False,
            modbus_register_type='HOLDING',
            modbus_slave=1,
            modbus_address=48,
            modbus_count=1
        ),
        DataStreamTemplate(
            id=starting_id + 21,
            feed_template=feed_template,
            label='phase3_cos_phi',
            name='phase3_cos_phi',
            measurement_unit='.',
            writable=False,
            modbus_register_type='HOLDING',
            modbus_slave=1,
            modbus_address=49,
            modbus_count=1
        ),
        DataStreamTemplate(
            id=starting_id + 22,
            feed_template=feed_template,
            label='t1_partial',
            name='t1_partial',
            measurement_unit='0.01 kWh',
            writable=True,
            modbus_register_type='HOLDING',
            modbus_slave=1,
            modbus_address=29,
            modbus_count=2,
            show_on_dashboard=True,
            default_minimum=0,
            default_maximum=100,
        ),
        DataStreamTemplate(
            id=starting_id + 23,
            feed_template=feed_template,
            label='t2_partial',
            name='t2_partial',
            measurement_unit='0.01 kWh',
            writable=True,
            modbus_register_type='HOLDING',
            modbus_slave=1,
            modbus_address=33,
            modbus_count=2,
            show_on_dashboard=True,
            default_minimum=0,
            default_maximum=100,
        ),
        DataStreamTemplate(
            id=starting_id + 24,
            feed_template=feed_template,
            label='tariff_register',
            name='tariff_register',
            measurement_unit='.',
            writable=True,
            modbus_register_type='HOLDING',
            modbus_slave=1,
            modbus_address=26,
            modbus_count=1
        ),
        DataStreamTemplate(
            id=starting_id + 25,
            feed_template=feed_template,
            label='status',
            name='status',
            measurement_unit='.',
            writable=True,
            modbus_register_type='HOLDING',
            modbus_slave=1,
            modbus_address=21,
            modbus_count=1
        ),
        DataStreamTemplate(
            id=starting_id + 26,
            feed_template=feed_template,
            label='WT1_partial_1',
            name='WT1_partial_1',
            measurement_unit='.',
            writable=True,
            modbus_register_type='HOLDING',
            modbus_slave=1,
            modbus_address=29,
            modbus_count=2
        ),
        DataStreamTemplate(
            id=starting_id + 27,
            feed_template=feed_template,
            label='WT1_partial_2',
            name='WT1_partial_2',
            measurement_unit='.',
            writable=True,
            modbus_register_type='HOLDING',
            modbus_slave=1,
            modbus_address=33,
            modbus_count=2
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


def create_test_data2():
    starting_id = 200000
    feed_template = FeedTemplate(
        id=starting_id,
        name=u"NIBE Modbus 40",
        dashboard_layout="GAUGES",
        modbus_bandwidth=9600,
        modbus_port='/dev/ttyS0',
        modbus_parity='EVEN',
        modbus_data_bits=8,
        modbus_stop_bits=1,
        modbus_timeout=5,
        modbus_endianness='BIG',
        modbus_polling_interval=120
    )
    feed = Feed(
        id=starting_id,
        template=feed_template,
        name=u"Instalacja pompy NIBE",
        description=u"Instalacja pompy NIBE",
        address=u"ul. Bysławska 82 lok. 312\n04-993 Warszawa",
        latitude=52.158427,
        longitude=21.198292,
        api_key='aaaa1tgDLBbzoghjCBDrpcD2NXUCP1WGFUDwm7baQTgmgueS5eU5c4W9EpLrnorJKC4DMfKe255YbwPvAJ7ppbD21NAs8XLk4XQb',
        created=pytz.utc.localize(datetime.datetime.utcnow())
    )
    feed.regenerate_activation_code()
    user = DBSession.query(User).filter(User.email == 'user@example.com').one()
    feed_user = FeedUser(
        id=starting_id,
        feed=feed,
        user=user,
        role='OWNER_PLUS'
    )
    DBSession.add_all([feed_template, feed, feed_user])
    data_stream_templates = [
        DataStreamTemplate(
            id=starting_id,
            feed_template=feed_template,
            name='Outdoor temperature (BT1)',
            label='outdoor_temp',
            measurement_unit=u'°C',
            writable=False,
            modbus_register_type='HOLDING',
            modbus_slave=1,
            modbus_address=40004,
            modbus_count=1
        ),
        DataStreamTemplate(
            id=starting_id + 1,
            feed_template=feed_template,
            name='Flow temperature (BT2)',
            label='flow_temp',
            measurement_unit=u'°C',
            writable=False,
            modbus_register_type='HOLDING',
            modbus_slave=1,
            modbus_address=40008,
            modbus_count=1
        ),
        DataStreamTemplate(
            id=starting_id + 2,
            feed_template=feed_template,
            name='Return temperature (BT3)',
            label='return_temp',
            measurement_unit=u'°C',
            writable=False,
            modbus_register_type='HOLDING',
            modbus_slave=1,
            modbus_address=40012,
            modbus_count=1
        ),
        DataStreamTemplate(
            id=starting_id + 3,
            feed_template=feed_template,
            name='Hot water, top (BT7)',
            label='hot_water_top',
            measurement_unit='?',
            writable=False,
            modbus_register_type='HOLDING',
            modbus_slave=1,
            modbus_address=40013,
            modbus_count=1
        ),
        DataStreamTemplate(
            id=starting_id + 4,
            feed_template=feed_template,
            name='Hot water middle (BT6)',
            label='hot_water_middle',
            measurement_unit='?',
            writable=False,
            modbus_register_type='HOLDING',
            modbus_slave=1,
            modbus_address=40014,
            modbus_count=1
        ),
        DataStreamTemplate(
            id=starting_id + 5,
            feed_template=feed_template,
            name='Brine in (BT10)',
            label='brine_in',
            measurement_unit='?',
            writable=False,
            modbus_register_type='HOLDING',
            modbus_slave=1,
            modbus_address=40014,
            modbus_count=1
        ),
        DataStreamTemplate(
            id=starting_id + 6,
            feed_template=feed_template,
            name='Brine out (BT11)',
            label='brine_out',
            measurement_unit='?',
            writable=False,
            modbus_register_type='HOLDING',
            modbus_slave=1,
            modbus_address=40014,
            modbus_count=1
        ),
        DataStreamTemplate(
            id=starting_id + 7,
            feed_template=feed_template,
            name='Room temperature (BT50)',
            label='room_temp',
            measurement_unit=u'°C',
            writable=False,
            modbus_register_type='HOLDING',
            modbus_slave=1,
            modbus_address=40033,
            modbus_count=1
        ),
        DataStreamTemplate(
            id=starting_id + 8,
            feed_template=feed_template,
            name='Degree minutes',
            label='degree_minutes',
            measurement_unit='?',
            writable=False,
            modbus_register_type='HOLDING',
            modbus_slave=1,
            modbus_address=43005,
            modbus_count=1
        ),
    ]
    DBSession.add_all(data_stream_templates)
    i = starting_id
    for data_stream_template in data_stream_templates:
        DBSession.add(
            DataStream(
                id=i,
                template=data_stream_template,
                feed=feed
            )
        )
        i += 1
    transaction.commit()

if __name__ == '__main__':
    sys.exit(main())
