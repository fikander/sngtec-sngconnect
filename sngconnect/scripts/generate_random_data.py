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
from sngconnect.database import Feed, DataStream
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
    DBSession.query(Feed).delete()
    DBSession.query(DataStream).delete()
    transaction.commit()
    cassandra.drop_keyspace(settings)
    cassandra.initialize_keyspace(settings)
    cassandra_connection_pool.initialize_connection_pool(settings)
    generate_data(feed_count)

def generate_data(feed_count):
    for i in range(1, feed_count + 1):
        feed = Feed(
            name=u"Feed %d" % i,
            description=u"Opis instalacji wprowadzony przez instalatora. Moze"
                        u" zawierac np. jakies notatki.",
            address=u"1600 Ampitheater Pkwy., Mountain View, CA",
            latitude=random.uniform(49.0, 54.833333),
            longitude=random.uniform(14.116666, 24.15),
            created=pytz.timezone('Europe/Warsaw').localize(
                datetime.datetime.now() - datetime.timedelta(days=80)
            )
        )
        DBSession.add(feed)
        for j in range(1, 3):
            data_stream = DataStream(
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
                minimal_value=random.uniform(-1000, 0),
                maximal_value=random.uniform(0, 1000),
                feed=feed
            )
            DBSession.add(data_stream)
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
            - datetime.timedelta(days=30)
        )
        end = pytz.utc.localize(datetime.datetime.utcnow())
        last_value = numpy.float128(2000)
        dates = []
        print "Generating..."
        j = 0
        while start < end:
            end -= datetime.timedelta(seconds=10)
            dates.append(end)
            last_value = numpy.float128(
                (
                    numpy.sin(numpy.float128(j) / numpy.float128(10.0))
                    * numpy.float128(20)
                    + numpy.float128(random.uniform(-100, 100))
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
