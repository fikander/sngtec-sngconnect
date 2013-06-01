import requests
import lxml.etree

from sngconnect.services.base import ServiceBase


class SMSService(ServiceBase):

    class SendingError(Exception):
        pass

    def __init__(self, *args, **kwargs):
        super(SMSService, self).__init__(*args, **kwargs)
        self._api_url = self.registry.settings['sngconnect.serwersms.url']
        self._api_login = self.registry.settings['sngconnect.serwersms.login']
        self._api_password = (
            self.registry.settings['sngconnect.serwersms.password']
        )

    def send_sms(self, recipients, message):
        request = {
            'akcja': 'wyslij_sms',
            'login': self._api_login,
            'haslo': self._api_password,
            'numer': ','.join(recipients),
            'wiadomosc': unicode(message).encode('ascii', 'strict'),
        }
        try:
            response = requests.post(self._api_url, request)
        except requests.ConnectionError, e:
            raise self.SendingError(
                "Error connecting to SMS server: {}.".format(str(e))
            )
        if response.status_code != 200:
            raise self.SendingError(
                "Server returned status code {}.".format(response.status_code)
            )
        try:
            response = lxml.etree.XML(response.content)
        except lxml.etree.XMLSyntaxError:
            raise self.SendingError("Invalid response XML syntax.")
        error = response.xpath('/SerwerSMS/Blad')
        if error:
            raise self.SendingError(error[0].text)
