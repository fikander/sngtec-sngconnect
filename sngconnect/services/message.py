import sqlalchemy as sql

from sngconnect.cassandra.confirmations import Confirmations
from sngconnect.services.base import ServiceBase
from sngconnect.services.notification import NotificationService
from sngconnect.database import DBSession, Message, User, FeedUser

class MessageService(ServiceBase):

    default_order = sql.desc(Message.date)

    def __init__(self, *args, **kwargs):
        super(MessageService, self).__init__(*args, **kwargs)
        self.notification_service = self.get_service(NotificationService)
        self.confirmations = Confirmations()

    def create_message(self, message):
        DBSession.add(message)
        if message.confirmation_required:
            if message.feed is not None:
                users = DBSession.query(User).join(
                    FeedUser
                ).filter(
                    FeedUser.feed == message.feed,
                    FeedUser.role_user == True
                ).all()
            else:
                users = DBSession.query(User).all()
            self.confirmations.set_unconfirmed(
                [user.id for user in users],
                message.id
            )
        if message.send_notifications:
            if message.feed is not None:
                self.notification_service.notify_users(
                    message.feed,
                    # TODO What to send in email subject and SMS notification?
                    "",
                    message.content
                )
            else:
                self.notification_service.notify_all(
                    # TODO What to send in email subject and SMS notification?
                    "",
                    message.content
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

    def get_feed_messages(self, feed):
        return DBSession.query(Message).filter(
            Message.feed == feed
        ).order_by(
            self.default_order
        ).all()

    def get_data_stream_messages(self, data_stream):
        return DBSession.query(Message).filter(
            Message.data_stream == data_stream
        ).order_by(
            self.default_order
        ).all()
