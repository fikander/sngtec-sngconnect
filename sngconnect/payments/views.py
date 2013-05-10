import decimal
import operator
import json
import datetime

from pyramid.view import view_config
from pyramid import httpexceptions
from pyramid.security import authenticated_userid

from sngconnect.payments import forms
from sngconnect.database import DBSession, Order
from sngconnect.services.user import UserService
from sngconnect.payments.payu.backend import PayUPaymentBackend

@view_config(
    route_name='sngconnect.payments.index',
    renderer='sngconnect.payments:templates/index.jinja2',
    permission='sngconnect.payments.access'
)
def index(request):
    order_maximum = int(
        request.registry['settings']['sngconnect.payments.order_maximum']
    )
    coin_prices = _get_coin_prices(request.registry['settings'])
    buy_form = forms.BuyForm(
        order_maximum=order_maximum,
        csrf_context=request
    )
    if request.method == 'POST':
        buy_form.process(request.POST)
        if buy_form.validate():
            coins = buy_form.coins.data
            user_service = UserService(request.registry)
            user = user_service.get_user(authenticated_userid(request))
            price = _get_price(coins, coin_prices)
            order = Order(
                status='PLACED',
                placed=datetime.datetime.utcnow(),
                user=user,
                client_email=user.email,
                audit_data=json.dumps({
                    'ip': request.client_addr,
                    'user_agent': request.user_agent,
                    'cookies': request.cookies.values(),
                    'accept_language': str(request.accept_language),
                }),
                coins=coins,
                price_net=price['price_net'],
                price_tax=price['price_tax'],
                price_gross=price['price_gross'],
                value_net=price['price_net'] * coins,
                value_tax=price['price_tax'] * coins,
                value_gross=price['price_gross'] * coins
            )
            DBSession.add(order)
            payment_backend = PayUPaymentBackend(
                request,
                request.route_url('sngconnect.payments.index'),
                request.route_url('sngconnect.payments.confirmation')
            )
            payment_backend.process_order(order)
            return httpexceptions.HTTPSeeOther(
            )
    return {
        'coin_prices': coin_prices,
        'buy_form': buy_form,
    }

@view_config(
    route_name='sngconnect.payments.confirmation',
    renderer='sngconnect.payments:templates/confirmation.jinja2',
    permission='sngconnect.payments.access'
)
def confirmation(request):
    return {}

@view_config(
    route_name='sngconnect.payments.calculate_price',
    request_method='GET',
    renderer='sngconnect.payments:templates/calculate_price.jinja2',
    permission='sngconnect.payments.access'
)
def calculate_price(request):
    if not request.is_xhr:
        raise httpexceptions.HTTPBadRequest()
    try:
        coins = int(request.GET['coins'])
    except (KeyError, ValueError):
        coins = None
    else:
        order_maximum = int(
            request.registry['settings']['sngconnect.payments.order_maximum']
        )
        if coins < 1 or coins > order_maximum:
            coins = None
    price = None
    value = None
    if coins is not None:
        price = _get_price(coins, _get_coin_prices(request.registry['settings']))
        price = price['price_gross']
        value = price * coins
    return {
        'price': price,
        'value': value,
    }

def _get_coin_prices(settings):
    SETTING_PREFIX = 'sngconnect.payments.coin_prices.'
    coin_prices = []
    for name, value in settings.iteritems():
        if not name.startswith(SETTING_PREFIX):
            continue
        coin_amount = int(name[len(SETTING_PREFIX):])
        price = decimal.Decimal(value)
        coin_prices.append((coin_amount, price))
    coin_prices = sorted(coin_prices, key=operator.itemgetter(0))
    result = []
    for i in range(len(coin_prices)):
        net = coin_prices[i][1]
        tax, gross = _calculate_tax_and_gross(net, settings)
        result.append({
            'minimum': coin_prices[i][0],
            'maximum': coin_prices[i + 1][0] - 1 if i + 1 < len(coin_prices) else None,
            'price_net': net,
            'price_tax': tax,
            'price_gross': gross,
        })
    return result

def _get_price(coins, coin_prices):
    price = None
    for position in coin_prices:
        if coins < position['minimum']:
            break
        price = position
    if price is None:
        raise ValueError("Invalid coin price configuration.")
    return price

def _calculate_tax_and_gross(net, settings):
    multiplier = decimal.Decimal(settings['sngconnect.payments.vat']) + 1
    gross = (net * multiplier).quantize(decimal.Decimal('0.01'))
    tax = gross - net
    return tax, gross
