# -*- coding: utf-8 -*-

from pyramid.view import view_config
from pyramid import httpexceptions
from sqlalchemy.orm import exc as database_exceptions
from pyramid.security import authenticated_userid

from sngconnect.translation import _
from sngconnect.telemetry import forms
from sngconnect.services.message import MessageService
from sngconnect.services.user import UserService

@view_config(
    route_name='sngconnect.telemetry.confirm_message',
    request_method='POST',
    permission='sngconnect.telemetry.access'
)
def confirm_message(request):
    form = forms.ConfirmMessageForm(csrf_context=request)
    form.process(request.POST)
    if form.validate():
        message_service = MessageService(request.registry)
        user_service = UserService(request.registry)
        try:
            message = message_service.get_message(form.id.data)
        except database_exceptions.NoResultFound:
            raise httpexceptions.HTTPNotFound()
        user = user_service.get_user(authenticated_userid(request))
        message_service.confirm_message(user, message)
        request.session.flash(
            _("Message successfully confirmed."),
            queue='success'
        )
        return httpexceptions.HTTPFound(
            request.headers.get('Referer', None) or
                request.route_url('sngconnect.telemetry.dashboard')
        )
    else:
        raise httpexceptions.HTTPBadRequest()
