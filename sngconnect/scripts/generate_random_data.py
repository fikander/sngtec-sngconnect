# -*- coding: utf-8 -*-

import os
import datetime
import random
import sys
import time

import numpy
import transaction
import sqlalchemy
from pyramid.paster import get_appsettings, setup_logging

from sngconnect import cassandra
from sngconnect.database import DBSession
from sngconnect.cassandra import connection_pool as cassandra_connection_pool
from sngconnect.database import System, Parameter
from sngconnect.cassandra.parameters import (Measurements, HourlyAggregates,
    DailyAggregates, MonthlyAggregates)

def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri> <magnitude>\n'
          '(example: "%s development.ini 5000")' % (cmd, cmd))
    sys.exit(1)

def main(argv=sys.argv):
    if len(argv) != 3:
        usage(argv)
    config_uri = argv[1]
    magnitude = int(argv[2])
    setup_logging(config_uri)
    settings = get_appsettings(config_uri)
    database_engine = sqlalchemy.engine_from_config(settings, 'database.')
    DBSession.configure(bind=database_engine)
    DBSession.query(System).delete()
    DBSession.query(Parameter).delete()
    transaction.commit()
    cassandra.drop_keyspace(settings)
    cassandra.initialize_keyspace(settings)
    cassandra_connection_pool.initialize_connection_pool(settings)
    generate_data(magnitude)

def generate_data(magnitude):
    for i in range(1, 2):
        system = System(name="System %d" % i)
        DBSession.add(system)
        for i in range(1, 2):
            parameter = Parameter(
                name="Parameter %d" % i,
                measurement_unit=random.choice([
                    u'kW',
                    u'm',
                    u'cm',
                    u'°C',
                    u'mm',
                    u'cm³',
                ]),
                writable=False,
                system=system
            )
            DBSession.add(parameter)
    transaction.commit()
    parameters = DBSession.query(Parameter).all()
    measurements = Measurements()
    i = 1
    count = len(parameters)
    for parameter in parameters:
        print "Parameter %d/%d:" % (i, count)
        i += 1
        data_points = []
        start = datetime.datetime.utcnow() - datetime.timedelta(days=60)
        end = datetime.datetime.utcnow()
        last_value = numpy.float128(2000)
        dates = []
        print "Generating..."
        j = 0
        while start < end:
            end -= datetime.timedelta(seconds=5)
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
                measurements.insert_data_points(parameter.id, data_points)
                print "Aggregating..."
                HourlyAggregates().recalculate_aggregates(parameter.id, dates)
                DailyAggregates().recalculate_aggregates(parameter.id, dates)
                MonthlyAggregates().recalculate_aggregates(parameter.id, dates)
                data_points = []
                dates = []
                print "%d done" % j
                time.sleep(5)
        print "Inserting..."
        measurements.insert_data_points(parameter.id, data_points)
        print "Aggregating..."
        HourlyAggregates().recalculate_aggregates(parameter.id, dates)
        DailyAggregates().recalculate_aggregates(parameter.id, dates)
        MonthlyAggregates().recalculate_aggregates(parameter.id, dates)
