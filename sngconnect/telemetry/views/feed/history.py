# -*- coding: utf-8 -*-

import datetime

import pytz
from pyramid.view import view_config
from pyramid import httpexceptions

from sngconnect.translation import _
from sngconnect.database import Message
from sngconnect.services.message import MessageService
from sngconnect.services.user import UserService
from sngconnect.telemetry import forms
from sngconnect.telemetry.views.feed.base import FeedViewBase

@view_config(
    route_name='sngconnect.telemetry.feed_history',
    renderer='sngconnect.telemetry:templates/feed/history.jinja2',
    permission='sngconnect.telemetry.access'
)
class FeedHistory(FeedViewBase):

    def __call__(self):
        message_service = MessageService(self.request.registry)
        comment_form = forms.CommentForm(csrf_context=self.request)
        if self.request.method == 'POST':
            comment_form.process(self.request.POST)
            if comment_form.validate():
                message = Message(
                    message_type='COMMENT',
                    date=pytz.utc.localize(datetime.datetime.utcnow()),
                    feed=self.feed,
                    author_id=self.user_id
                )
                comment_form.populate_obj(message)
                message_service.create_message(message)
                self.request.session.flash(
                    _("Your comment has been successfuly saved."),
                    queue='success'
                )
                return httpexceptions.HTTPFound(
                    self.request.route_url(
                        'sngconnect.telemetry.feed_history',
                        feed_id=self.feed.id
                    )
                )
            else:
                self.request.session.flash(
                    _(
                        "There were some problems with your request."
                        " Please check the form for error messages."
                    ),
                    queue='error'
                )
        user_service = UserService(self.request.registry)
        filter_form = forms.FilterMessagesForm(
            self.feed,
            user_service.get_all_feed_users(self.feed),
            self.feed.template.data_stream_templates,
            message_service,
            self.request.GET
        )
        messages = filter_form.get_messages()
        self.context.update({
            'comment_form': comment_form,
            'filter_form': filter_form,
            'messages': [
                {
                    'id': message.id,
                    'message_type': message.message_type,
                    'data_stream': (
                        {
                            'id': message.data_stream.id,
                            'name': message.data_stream.name,
                            'url': self.request.route_url(
                                (
                                    'sngconnect.telemetry.feed_data_stream'
                                    if not message.data_stream.writable else
                                    'sngconnect.telemetry.feed_settings'
                                ),
                                feed_id=message.data_stream.feed_id,
                                data_stream_label=message.data_stream.label
                            ),
                        }
                        if message.data_stream is not None
                        else None
                    ),
                    'author': (
                        {
                            'id': message.author.id,
                            'name': message.author.name
                        }
                        if message.author is not None
                        else None
                    ),
                    'content': message.content,
                    'date': message.date,
                }
                for message in messages
            ],
        })
        return self.context
