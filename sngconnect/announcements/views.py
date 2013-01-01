import datetime

import pytz
from pyramid.view import view_config
from pyramid import httpexceptions

from sngconnect.translation import _
from sngconnect.announcements import forms
from sngconnect.services.message import MessageService
from sngconnect.database import DBSession, Message

@view_config(
    route_name='sngconnect.announcements.announcements',
    renderer='sngconnect.announcements:templates/announcements.jinja2',
    permission='sngconnect.announcements.access'
)
def announcements(request):
    announcement_form = forms.CreateAnnouncementForm(csrf_context=request)
    if request.method == 'POST':
        announcement_form.process(request.POST)
        if announcement_form.validate():
            message = Message(
                message_type='ANNOUNCEMENT',
                date=pytz.utc.localize(datetime.datetime.utcnow())
            )
            announcement_form.populate_obj(message)
            DBSession.add(message)
            request.session.flash(
                _("Announcement has been successfuly sent."),
                queue='success'
            )
            return httpexceptions.HTTPFound(
                request.route_url('sngconnect.announcements.announcements')
            )
        else:
            request.session.flash(
                _(
                    "There were some problems with your request."
                    " Please check the form for error messages."
                ),
                queue='error'
            )
    messages = MessageService(request).get_announcements()
    return {
        'announcement_form': announcement_form,
        'messages': messages,
    }
