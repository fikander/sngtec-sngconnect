import datetime

from sqlalchemy.orm import exc as database_exceptions
from pyramid.view import view_config
from pyramid import httpexceptions
from pyramid.security import authenticated_userid

from sngconnect.translation import _
from sngconnect.database import DBSession, Feed, FeedUser, User


@view_config(
    route_name='sngconnect.telemetry.feed_inactive',
    renderer='sngconnect.telemetry:templates/feed/inactive.jinja2',
    permission='sngconnect.telemetry.access'
)
def inactive(request):
    user_id = authenticated_userid(request)
    try:
        user = DBSession.query(User).filter(
            User.id == user_id
        ).one()
    except database_exceptions.NoResultFound:
        raise httpexceptions.HTTPForbidden()
    try:
        feed = DBSession.query(Feed).filter(
            Feed.id == request.matchdict['feed_id']
        ).one()
    except database_exceptions.NoResultFound:
        raise httpexceptions.HTTPNotFound()
    try:
        feed_user = DBSession.query(FeedUser).filter(
            FeedUser.feed_id == feed.id,
            FeedUser.user_id == user_id
        ).one()
    except database_exceptions.NoResultFound:
        raise httpexceptions.HTTPNotFound()
    if feed_user.paid:
        raise httpexceptions.HTTPSeeOther(
            request.route_url(
                'sngconnect.telemetry.feed_dashboard',
                feed_id=feed.id
            )
        )
    settings = request.registry['settings']
    prices = {
        'OWNER_STANDARD': int(settings['sngconnect.prices.owner_standard.activation']),
        'OWNER_PLUS': int(settings['sngconnect.prices.owner_plus.activation']),
        'MAINTAINER_PLUS': int(settings['sngconnect.prices.owner_plus.activation']),
    }
    price = prices[feed_user.role]
    if request.method == 'POST':
        if price <= user.tokens:
            if user.last_payment is None:
                user.last_payment = datetime.datetime.utcnow()
            user.tokens -= price
            DBSession.add(user)
            feed_user.paid = True
            DBSession.add(feed_user)
            request.session.flash(
                _("The feed has been successfully activated."),
                queue='success'
            )
            return httpexceptions.HTTPSeeOther(
                request.route_url(
                    'sngconnect.telemetry.feed_dashboard',
                    feed_id=feed.id
                )
            )
        else:
            request.session.flash(
                _("You don't have enough tokens for setup fee."),
                queue='error'
            )
    return {
        'price': price,
    }
