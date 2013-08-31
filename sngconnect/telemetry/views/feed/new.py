import datetime

import pytz
import sqlalchemy as sql
from sqlalchemy.orm import exc as database_exceptions
from pyramid.view import view_config
from pyramid import httpexceptions
from pyramid.i18n import get_locale_name
from pyramid.security import authenticated_userid

from sngconnect.translation import _
from sngconnect.database import (DBSession, Feed, FeedUser, User,
    FeedTemplate, DataStreamTemplate, DataStream)
from sngconnect.telemetry import forms


@view_config(
    route_name='sngconnect.telemetry.feeds.new',
    renderer='sngconnect.telemetry:templates/feed/new.jinja2',
    permission='sngconnect.telemetry.create_feed'
)
def feeds_new(request):
    try:
        user = DBSession.query(User).filter(
            User.id == authenticated_userid(request)
        ).one()
    except database_exceptions.NoResultFound:
        raise httpexceptions.HTTPForbidden()
    feed_templates = DBSession.query(FeedTemplate).order_by(
        sql.asc(FeedTemplate.name)
    )
    if user.role_maintainer == True:
        forced_user = None
    else:
        forced_user = user
    create_form = forms.CreateFeedForm(
        feed_templates,
        forced_user,
        locale=get_locale_name(request),
        csrf_context=request
    )
    if request.method == 'POST':
        create_form.process(request.POST)
        if create_form.validate():
            feed = Feed()
            create_form.populate_obj(feed)
            feed.created = pytz.utc.localize(datetime.datetime.utcnow())
            feed.regenerate_api_key()
            feed.regenerate_activation_code()
            DBSession.add(feed)
            # need to save Feed within transaction to get it's key id
            DBSession.flush([feed])
            # create actual Datastreams for this Feed
            data_stream_templates = DBSession.query(DataStreamTemplate).filter(
                DataStreamTemplate.feed_template_id == feed.template_id
            )
            for data_stream_template in data_stream_templates:
                DBSession.add(
                    DataStream(
                        template=data_stream_template,
                        feed=feed
                    )
                )
            # set up user permissions
            feed_user = FeedUser(
                feed=feed,
                role='OWNER_BASIC'
            )
            if forced_user is None:
                feed_user.user = create_form.get_owner()
                feed_maintainer = FeedUser(
                    feed=feed,
                    user=user,
                    role='MAINTAINER_PLUS'
                )
                DBSession.add(feed_maintainer)
            else:
                feed_user.user = user
            DBSession.add(feed_user)
            request.session.flash(
                _(
                    "New device has been added. Go to the device dashboard to"
                    " obtain the activation code."
                ),
                queue='success'
            )
            return httpexceptions.HTTPFound(
                request.route_url('sngconnect.telemetry.dashboard')
            )
        else:
            request.session.flash(
                _(
                    "There were some problems with your request."
                    " Please check the form for error messages."
                ),
                queue='error'
            )
    return {
        'create_form': create_form,
    }
