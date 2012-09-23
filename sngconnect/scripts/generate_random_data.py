# -*- coding: utf-8 -*-

import os
import datetime
import random
import sys
import decimal

import transaction
import sqlalchemy
from pyramid.paster import get_appsettings, setup_logging

from sngconnect.database import DBSession
from sngconnect.cassandra import connection_pool as cassandra_connection_pool
from sngconnect.database import System, Parameter
from sngconnect.cassandra.parameters import (Measurements, HourlyAggregates,
    DailyAggregates, MonthlyAggregates, YearlyAggregates)

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
    cassandra_connection_pool.initialize_connection_pool(settings)
    generate_data(magnitude)

def generate_data(magnitude):
    for i in range(1, 3):
        system = System(name="System %d" % i)
        DBSession.add(system)
        for i in range(1, 5):
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
        data_points = []
        start = datetime.datetime.utcnow() - datetime.timedelta(days=30)
        end = datetime.datetime.utcnow()
        last_value = decimal.Decimal(0)
        dates = []
        print "Generating..."
        j = 0
        while start < end:
            start += datetime.timedelta(minutes=1)
            dates.append(start)
            last_value = (
                (decimal.Decimal(random.uniform(-500000, 500000)) + last_value)
                / 2
            )
            data_points.append((
                start,
                last_value
            ))
            j += 1
            if j % 1000000 == 0:
                print "Inserting..."
                measurements.insert_data_points(parameter.id, data_points)
                print "Aggregating..."
                HourlyAggregates().recalculate_aggregates(parameter.id, dates)
                DailyAggregates().recalculate_aggregates(parameter.id, dates)
                MonthlyAggregates().recalculate_aggregates(parameter.id, dates)
                YearlyAggregates().recalculate_aggregates(parameter.id, dates)
                data_points = []
                dates = []
                print "%d done" % j
        print "Inserting..."
        measurements.insert_data_points(parameter.id, data_points)
        print "Aggregating..."
        HourlyAggregates().recalculate_aggregates(parameter.id, dates)
        DailyAggregates().recalculate_aggregates(parameter.id, dates)
        MonthlyAggregates().recalculate_aggregates(parameter.id, dates)
        YearlyAggregates().recalculate_aggregates(parameter.id, dates)
