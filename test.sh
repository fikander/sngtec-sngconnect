#!/bin/bash
#
# Usage as for nosetests
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

echo "Dropping database..."
sudo -u postgres dropdb -e sngconnect_testing

echo "Done."
