sngconnect README
==================

Getting Started
---------------

- cd <directory containing this file>

- $venv/bin/python setup.py develop

- $venv/bin/sng_initialize_database development.ini

- $venv/bin/sng_initialize_cassandra development.ini

- $venv/bin/sng_generate_random_data development.ini 1

- $venv/bin/pserve development.ini --reload

Translation
-----------

- cd <directory containing this file>

- $venv/bin/python setup.py extract_messages

- $venv/bin/python setup.py update_catalog

- $venv/bin/python setup.py compile_catalog
