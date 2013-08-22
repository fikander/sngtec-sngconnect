sngconnect README
==================

Getting Started
---------------

- Install Vagrant - http://www.vagrantup.com

   $ cd <directory containing this file>
   $ vagrant up

- Optional to update vagrant installation (e.g. after puppet changes):

   $ vagrant provision

- Application is now available on localhost:8080

   $ vagrant ssh
   $ . environment/bin/activate
   $ sng_create_test_users /vagrant/development.ini
   $ sng_generate_random_data /vagrant/development.ini 1
   $ sng_create_test_data /vagrant/development.ini

- Run tests

   # recommended:
   $ ./test.sh --tests sngconnect.tests

   # all tests via setup.py:
   $ python ./setup.py test

   # single test using nosetests:
   $ python ./setup.py nosetests --tests sngconnect.tests.api.views:TestActivate.test_invalid_ids
   $ nosetests --tests sngconnect.tests.api.views:TestActivate.test_invalid_ids

- pserve test server runs via screen (use 'screen -r' to see output)

   $ screen -r

- Optional to update test scripts (sng_*)

   $ python ./setup.py install

Translation
-----------

   $ cd <directory containing this file>
   $ vagrant ssh
   $ . environment/bin/activate
   $ cd /vagrant
   $ python setup.py extract_messages
   $ python setup.py update_catalog
   $ python setup.py compile_catalog

FAQ
---

1. How to wipe out Postgres sngconnect database:

- ssh to vagrant

   $ vagrant ssh

- kill all active postgres processes with connections
- launch CLI as postgres and drop database

   $ sudo -u postgres psql
   postgres=# \l
   postgres=# DROP DATABASE sngconnect;

- puppet can create new database, so exist vagrant SSH and run puppet:

   $ vagrant provision
