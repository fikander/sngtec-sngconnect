#!/usr/bin/env python

import datetime
import os
import csv
import gzip

import numpy
import numpy.random

BASE_PATH = os.path.dirname(__file__)

DATA_POINTS_FILENAME = os.path.join(
    BASE_PATH,
    'data_points.csv.gz'
)
HOURLY_AGGREGATES_FILENAME = os.path.join(
    BASE_PATH,
    'hourly_aggregates.csv.gz'
)
DAILY_AGGREGATES_FILENAME = os.path.join(
    BASE_PATH,
    'daily_aggregates.csv.gz'
)
MONTHLY_AGGREGATES_FILENAME = os.path.join(
    BASE_PATH,
    'monthly_aggregates.csv.gz'
)

if __name__ == '__main__':

    date = datetime.datetime.now()
    end_date = date - datetime.timedelta(days=2)

    iteration = numpy.float64(0)
    last_value = numpy.float64(0)

    data_points = []

    print "Generating data..."

    while date > end_date:
        iteration += 1
        last_value = (
            (
                last_value * 3
                + (numpy.sin(iteration) * 20)
                + numpy.random.randint(-50, 50)
            )
            / 4
        )
        data_points.append((
            date,
            last_value
        ))
        date -= datetime.timedelta(
            microseconds=numpy.random.randint(5, 60000000)
        )

    hourly_aggregates = {}
    daily_aggregates = {}
    monthly_aggregates = {}

    print "Aggregating hours..."

    for date, value in data_points:
        key = date.replace(minute=0, second=0, microsecond=0)
        hourly_aggregates.setdefault(
            key,
            {
                'minimum': None,
                'maximum': None,
                'sum': numpy.float64(0),
                'count': 0,
            }
        )
        if hourly_aggregates[key]['minimum'] is None:
            hourly_aggregates[key]['minimum'] = value
        else:
            hourly_aggregates[key]['minimum'] = min(
                hourly_aggregates[key]['minimum'],
                value
            )
        if hourly_aggregates[key]['maximum'] is None:
            hourly_aggregates[key]['maximum'] = value
        else:
            hourly_aggregates[key]['maximum'] = max(
                hourly_aggregates[key]['maximum'],
                value
            )
        hourly_aggregates[key]['sum'] += value
        hourly_aggregates[key]['count'] += 1

    print "Aggregating days..."

    for date, value in data_points:
        key = date.replace(hour=0, minute=0, second=0, microsecond=0)
        daily_aggregates.setdefault(
            key,
            {
                'minimum': None,
                'maximum': None,
                'sum': numpy.float64(0),
                'count': 0,
            }
        )
        if daily_aggregates[key]['minimum'] is None:
            daily_aggregates[key]['minimum'] = value
        else:
            daily_aggregates[key]['minimum'] = min(
                daily_aggregates[key]['minimum'],
                value
            )
        if daily_aggregates[key]['maximum'] is None:
            daily_aggregates[key]['maximum'] = value
        else:
            daily_aggregates[key]['maximum'] = max(
                daily_aggregates[key]['maximum'],
                value
            )
        daily_aggregates[key]['sum'] += value
        daily_aggregates[key]['count'] += 1

    print "Aggregating months..."

    for date, value in data_points:
        key = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_aggregates.setdefault(
            key,
            {
                'minimum': None,
                'maximum': None,
                'sum': numpy.float64(0),
                'count': 0,
            }
        )
        if monthly_aggregates[key]['minimum'] is None:
            monthly_aggregates[key]['minimum'] = value
        else:
            monthly_aggregates[key]['minimum'] = min(
                monthly_aggregates[key]['minimum'],
                value
            )
        if monthly_aggregates[key]['maximum'] is None:
            monthly_aggregates[key]['maximum'] = value
        else:
            monthly_aggregates[key]['maximum'] = max(
                monthly_aggregates[key]['maximum'],
                value
            )
        monthly_aggregates[key]['sum'] += value
        monthly_aggregates[key]['count'] += 1

    print "Writing data points..."

    with gzip.open(DATA_POINTS_FILENAME, 'w') as file:
        writer = csv.writer(file)
        for date, value in data_points:
            writer.writerow((
                date.isoformat(),
                str(value)
            ))

    print "Writing hourly aggregates..."

    with gzip.open(HOURLY_AGGREGATES_FILENAME, 'w') as file:
        writer = csv.writer(file)
        for date, values in hourly_aggregates.iteritems():
            writer.writerow((
                date.isoformat(),
                values['minimum'],
                values['maximum'],
                values['sum'],
                int(values['count']),
            ))

    print "Writing daily aggregates..."

    with gzip.open(DAILY_AGGREGATES_FILENAME, 'w') as file:
        writer = csv.writer(file)
        for date, values in daily_aggregates.iteritems():
            writer.writerow((
                date.isoformat(),
                values['minimum'],
                values['maximum'],
                values['sum'],
                int(values['count']),
            ))

    print "Writing monthly aggregates..."

    with gzip.open(MONTHLY_AGGREGATES_FILENAME, 'w') as file:
        writer = csv.writer(file)
        for date, values in monthly_aggregates.iteritems():
            writer.writerow((
                date.isoformat(),
                values['minimum'],
                values['maximum'],
                values['sum'],
                int(values['count']),
            ))

    print "Done."
