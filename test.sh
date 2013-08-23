#!/bin/bash
#
# Usage as for nosetests, e.g.:
#    $ ./test.sh --tests sngconnect.tests
# This script creates testing database and drops it after tests have
# been executed.
#

if [ `sudo -u postgres psql -l | grep sngconnect_testing | wc -l` = 0 ]
then
    echo "Creating test database..."
    sudo -u postgres createdb -e -O sngconnect sngconnect_testing
fi

echo "Calling nosetests..."
nosetests $@
#python setup.py test

echo "Dropping database..."
sudo -u postgres dropdb -e sngconnect_testing

echo "Done."
