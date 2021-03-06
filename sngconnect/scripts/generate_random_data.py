# -*- coding: utf-8 -*-

import os
import datetime
import random
import sys
import time

import pytz
import numpy
import transaction
import sqlalchemy
from pyramid.paster import get_appsettings, setup_logging

from sngconnect import cassandra
from sngconnect.database import DBSession
from sngconnect.cassandra import connection_pool as cassandra_connection_pool
from sngconnect.database import (User, FeedTemplate, Feed, DataStreamTemplate,
    DataStream, FeedUser, ChartDefinition)
from sngconnect.cassandra.data_streams import (Measurements, HourlyAggregates,
    DailyAggregates, MonthlyAggregates, LastDataPoints)


def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri> <feed_count>\n'
          '(example: "%s development.ini 3")' % (cmd, cmd))
    sys.exit(1)


def main(argv=sys.argv):
    if len(argv) != 3:
        usage(argv)
    config_uri = argv[1]
    feed_count = int(argv[2])
    setup_logging(config_uri)
    settings = get_appsettings(config_uri)
    database_engine = sqlalchemy.engine_from_config(settings, 'database.')
    DBSession.configure(bind=database_engine)
    cassandra.drop_keyspace(settings)
    cassandra.initialize_keyspace(settings)
    cassandra_connection_pool.initialize_connection_pool(settings)
    generate_data(feed_count, 1, 30, 300)


def generate_data(feed_count, data_streams_count=4, days=30, resolution_seconds=300):
    starting_id = 1000000

    for i in range(1, feed_count + 1):

        for j in range(1, data_streams_count + 1):
            DBSession.query(DataStream).filter(
                DataStream.id == starting_id+j*i
            ).delete()
            DBSession.query(DataStreamTemplate).filter(
                DataStreamTemplate.id == starting_id+j*i
            ).delete()

        DBSession.query(ChartDefinition).filter(
            ChartDefinition.feed_template_id == starting_id+1
        ).delete()
        DBSession.query(FeedUser).filter(
            FeedUser.feed_id == starting_id+i
        ).delete()
        DBSession.query(Feed).filter(
            Feed.id == starting_id+i
        ).delete()
        DBSession.query(FeedTemplate).filter(
            FeedTemplate.id == starting_id+i
        ).delete()

        user = DBSession.query(User).filter(User.email == 'user@example.com').one()
        #kid = DBSession.query(User).filter(User.email == 'kid@example.com').one()

        feed_template = FeedTemplate(
            id=starting_id + i,
            name=u"[TEST] Feed template %d" % i,
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
            id=starting_id + i,
            template=feed_template,
            name=u"[TEST] Feed %d" % i,
            description=u"Opis instalacji wprowadzony przez instalatora. Moze"
                        u" zawierac np. jakies notatki.",
            address=u"1600 Ampitheater Pkwy., Mountain View, CA",
            latitude=random.uniform(49.0, 54.833333),
            longitude=random.uniform(14.116666, 24.15),
            created=pytz.timezone('Europe/Warsaw').localize(
                datetime.datetime.now() - datetime.timedelta(days=80)
            )
        )
        feed.regenerate_api_key()
        feed.regenerate_activation_code()

        feed_user_user = FeedUser(role='OWNER_PLUS')
        feed.feed_users.append(feed_user_user)
        user.feed_users.append(feed_user_user)

        #feed_user_kid = FeedUser(role='USER_PLUS')
        #kid.feed_users.append(feed_user_kid)
        #feed.feed_users.append(feed_user_kid)
        DBSession.add_all([
            feed_template,
            feed,
            feed_user_user,
            #feed_user_kid,
        ])
        for j in range(1, data_streams_count + 1):
            data_stream_template = DataStreamTemplate(
                id=starting_id + j * i,
                feed_template=feed_template,
                label=('data_stream_%d' % j),
                name=u"DataStream %d" % j,
                description=u"Tutaj można wyświetlić aktualną temperaturę wody"
                            u" na wyjściu z pompy ciepła zasilającej feed"
                            u" grzewczy.",
                measurement_unit=random.choice([
                    u'kW',
                    u'm',
                    u'cm',
                    u'°C',
                    u'mm',
                    u'cm³',
                ]),
                writable=random.choice([True, False, False]),
                show_on_dashboard=random.choice((True, False)),
                modbus_register_type='HOLDING',
                modbus_slave=1,
                modbus_address=j,
                modbus_count=random.choice([1, 2])
            )
            data_stream = DataStream(
                id=starting_id + j * i,
                template=data_stream_template,
                feed=feed
            )
            DBSession.add_all([data_stream_template, data_stream])
    transaction.commit()

    feed_templates = DBSession.query(FeedTemplate).all()
    for feed_template in feed_templates:
        for i in range(1, 4):
            chart_definition = ChartDefinition(
                feed_template=feed_template,
                data_stream_templates=random.sample(
                    feed_template.data_stream_templates,
                    random.randint(1, len(feed_template.data_stream_templates))
                ),
                name=u"Chart definition %d" % i,
                chart_type=random.choice(('LINEAR', 'DIFFERENTIAL')),
                show_on_dashboard=random.choice((True, False))
            )
            DBSession.add(chart_definition)
    transaction.commit()

    data_streams = DBSession.query(DataStream).all()
    measurements = Measurements()
    i = 1
    count = len(data_streams)
    for data_stream in data_streams:
        print "DataStream %d/%d:" % (i, count)
        i += 1
        data_points = []
        start = (
            pytz.utc.localize(datetime.datetime.utcnow())
            - datetime.timedelta(days=days)
        )
        end = pytz.utc.localize(datetime.datetime.utcnow())
        last_value = numpy.float64(2000)
        dates = []
        print "Generating..."
        j = 0
        while start < end:
            end -= datetime.timedelta(seconds=resolution_seconds)
            dates.append(end)
            last_value = numpy.float64(
                (
                    numpy.sin(numpy.float64(j) / numpy.float64(10.0))
                    * numpy.float64(20)
                    + numpy.float64(random.uniform(-100, 100))
                ) + (last_value * 2)
            ) / 2
            data_points.append((
                end,
                last_value
            ))
            j += 1
            if j % 10000 == 0:
                print "Inserting..."
                measurements.insert_data_points(data_stream.id, data_points)
                print "Aggregating..."
                HourlyAggregates().recalculate_aggregates(data_stream.id, dates)
                DailyAggregates().recalculate_aggregates(data_stream.id, dates)
                MonthlyAggregates().recalculate_aggregates(data_stream.id, dates)
                data_points = []
                dates = []
                print "%d done" % j
                time.sleep(5)
        print "Inserting..."
        measurements.insert_data_points(data_stream.id, data_points)
        print "Aggregating..."
        HourlyAggregates().recalculate_aggregates(data_stream.id, dates)
        DailyAggregates().recalculate_aggregates(data_stream.id, dates)
        MonthlyAggregates().recalculate_aggregates(data_stream.id, dates)
        print "Updating last values..."
        LastDataPoints().update(data_stream.feed.id, data_stream.id)

if __name__ == '__main__':
    sys.exit(main())
