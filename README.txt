sngconnect README
==================

Getting Started
---------------

- Install Vagrant - http://www.vagrantup.com

- cd <directory containing this file>

- vagrant up

- Application is now available on localhost:8080

- vagrant ssh

- . environment/bin/activate

- sng_generate_random_data /vagrant/development.ini 1

- sng_create_testing_data /vagrant/development.ini

Translation
-----------

- cd <directory containing this file>

- vagrant ssh

- . environment/bin/activate

- cd /vagrant

- python setup.py extract_messages

- python setup.py update_catalog

- python setup.py compile_catalog
