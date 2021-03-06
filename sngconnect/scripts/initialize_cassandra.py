import os
import sys

from pyramid.paster import get_appsettings, setup_logging

from sngconnect.cassandra import initialize_keyspace


def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri>\n'
          '(example: "%s development.ini")' % (cmd, cmd))
    sys.exit(1)


def main(argv=sys.argv):
    if len(argv) != 2:
        usage(argv)
    config_uri = argv[1]
    setup_logging(config_uri)
    settings = get_appsettings(config_uri)
    initialize_keyspace(settings)

if __name__ == '__main__':
    sys.exit(main())
