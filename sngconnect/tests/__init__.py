import logging

from pyramid import testing

class TestMixin(object):

    def setUp(self):
        logging.basicConfig(
            format='%(levelname)s: %(message)s',
            level=logging.WARNING
        )
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()
