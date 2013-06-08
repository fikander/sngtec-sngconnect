import sqlalchemy as sql

from sngconnect.cassandra.confirmations import Confirmations
from sngconnect.services.base import ServiceBase
from sngconnect.services.notification import NotificationService
from sngconnect.database import (DBSession, Message, User, FeedUser,
    DataStream, DataStreamTemplate)


class MessageService(ServiceBase):

    default_order = sql.desc(Message.date)

    def __init__(self, *args, **kwargs):
        super(MessageService, self).__init__(*args, **kwargs)
        self.notification_service = self.get_service(NotificationService)
        self.confirmations = Confirmations()

    def get_message(self, id):
        return DBSession.query(Message).filter(
            Message.id == id
        ).one()

    def create_message(self, message):
        DBSession.add(message)
        DBSession.flush()
        if message.confirmation_required:
            if message.feed is not None:
                users = DBSession.query(User).join(
                    FeedUser
                ).filter(
                    FeedUser.feed == message.feed,
                ).all()
            else:
                users = DBSession.query(User).all()
            self.confirmations.set_unconfirmed(
                [user.id for user in users],
                message.id
            )
        if message.send_notifications:
            if message.feed is not None:
                self.notification_service.notify_feed_users(
                    message.feed,
                    # TODO What to send in email subject and SMS notification?
                    "",
                    message
                )
            else:
                self.notification_service.notify_all(
                    # TODO What to send in email subject and SMS notification?
                    "",
                    message
                )

    def get_announcements(self):
        return DBSession.query(Message).filter(
            Message.message_type == u'ANNOUNCEMENT'
        ).order_by(
            self.default_order
        ).all()

    def get_unconfirmed_messages(self, user, feed=None):
        message_ids = self.confirmations.get_unconfirmed(user.id)
        query = DBSession.query(Message).filter(
            Message.id.in_(message_ids)
        )
        if feed is not None:
            query = query.filter(
                Message.feed == feed
            )
        return query.order_by(
            self.default_order
        ).all()

    def confirm_message(self, user, message):
        self.confirmations.set_confirmed(user.id, [message.id])

    def get_feed_messages(self, feed, data_stream_template_id=None,
            author_id=None):
        query = DBSession.query(Message).filter(
            Message.feed == feed
        )
        if author_id is not None:
            query = query.filter(
                Message.author_id == author_id
            )
        if data_stream_template_id is not None:
            if data_stream_template_id == -1:
                query = query.filter(
                    Message.data_stream == None
                )
            else:
                query = query.join(
                    DataStream,
                    DataStreamTemplate
                ).filter(
                    DataStreamTemplate.id == data_stream_template_id
                )
        return query.order_by(
            self.default_order
        ).all()

    def get_data_stream_messages(self, data_stream):
        return DBSession.query(Message).filter(
            Message.data_stream == data_stream
        ).order_by(
            self.default_order
        ).all()
