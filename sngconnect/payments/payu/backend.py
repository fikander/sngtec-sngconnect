import uuid
import hashlib

import requests
from lxml import etree
from lxml.builder import ElementMaker

from sngconnect.translation import _
from sngconnect.database import DBSession, PayUSession
from sngconnect.payments.payu.library import (
    get_schema,
    NAMESPACE,
    XML_TYPEMAP,
)

class PayUPaymentBackend(object):

    class Error(Exception):
        pass

    def __init__(self, request, cancel_url, complete_url):
        self.request = request
        self.cancel_url = cancel_url
        self.complete_url = complete_url
        self._notify_url = request.route_url('sngconnect.payments.payu.notify')
        settings = request.registry['settings']
        self._currency_code = settings['sngconnect.currency_code']
        self._service_url = settings['sngconnect.payments.payu.service_url']
        self._pos_id = settings['sngconnect.payments.payu.pos_id']
        self._pos_authorization_key = (
            settings['sngconnect.payments.payu.pos_authorization_key']
        )
        self._signature_key = (
            settings['sngconnect.payments.payu.signature_key']
        )
        self._schema = get_schema()

    def process_order(self, order):
        e = ElementMaker(
            namespace=NAMESPACE,
            typemap=XML_TYPEMAP
        )
        request_id = uuid.uuid4().hex
        session = PayUSession(
            status='CREATED',
            order=order,
            create_order_request_id=request_id,
        )
        DBSession.add(session)
        DBSession.flush()
        request = e.OpenPayU(
            e.HeaderRequest(
                e.SenderName('com.sngconnect.payments'),
                e.Version('1.0'),
                e.Algorithm('SHA-256'),
            ),
            e.OrderDomainRequest(
                e.OrderCreateRequest(
                    e.ReqId(request_id),
                    e.NotifyUrl(self._notify_url),
                    e.OrderCancelUrl(self.cancel_url),
                    e.OrderCompleteUrl(self.complete_url),
                    e.CustomerIp(self.request.client_addr),
                    e.Order(
                        e.MerchantPosId(self._pos_id),
                        e.SessionId(session.id),
                        e.OrderCreateDate(order.placed),
                        e.OrderDescription(_("SNG:connect coins")),
                        e.OrderType('VIRTUAL'),
                        e.ShoppingCart(
                            e.GrandTotal(int(order.value_gross * 100)),
                            e.CurrencyCode(self._currency_code),
                            e.ShoppingCartItems(
                                e.ShoppingCartItem(
                                    e.Product(
                                        e.Name(_("SNG:connect coin")),
                                        e.UnitPrice(
                                            e.Net(int(order.price_net * 100)),
                                            e.Gross(int(order.price_gross * 100)),
                                            e.Tax(int(order.price_tax * 100)),
                                            e.CurrencyCode(self._currency_code),
                                        )
                                    ),
                                    e.Quantity(order.coins)
                                )
                            )
                        ),
                        e.MerchantAuthorizationKey(self._pos_authorization_key)
                    )
                )
            )
        )

        self._schema.assertValid(request)
        request_string = etree.tostring(request)

        signature = hashlib.sha256(
            request_string + self._signature_key
        ).hexdigest()
        response_string = requests.post(
            self._service_url + 'co/openpayu/OrderCreateRequest',
            data={
                'DOCUMENT': request_string,
            },
            headers={
                'OpenPayu-Signature': ';'.join((
                    'sender=' + self._pos_id,
                    'signature=' + signature,
                    'algorithm=SHA-256',
                    'content=DOCUMENT',
                )),
            }
        )

        response = etree.parse(response_string)
        self._schema.assertValid(response)

        status_code = response.xpath(
            '/o:OpenPayU/o:OrderDomainResponse/o:OrderCreateResponse/o:Status'
            '/o:StatusCode',
            namespaces={
                'o': NAMESPACE,
            }
        )[0]
        if status_code != 'OPENPAYU_SUCCESS':
            raise self.Error("Bad response status: %s" % status_code)

        return self._service_url + 'co/summary'
