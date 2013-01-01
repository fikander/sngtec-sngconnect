import sqlalchemy as sql

from sngconnect.services.base import ServiceBase
from sngconnect.services.notification import NotificationService
from sngconnect.database import DBSession, Message

class MessageService(ServiceBase):

    default_order = sql.desc(Message.date)

    def create_message(self, message):
        DBSession.add(message)
        if message.send_notifications:
            notification_service = self.get_service(NotificationService)
            if message.feed is not None:
                notification_service.notify_users(
                    message.feed,
                    # TODO What to send in email subject and SMS notification?
                    "",
                    message.content
                )
            else:
                notification_service.notify_all(
                    # TODO What to send in email subject and SMS notification?
                    "",
                    message.content
                )

    def get_important_messages(self, feed):
        return DBSession.query(Message).filter(
            Message.feed == feed,
            Message.message_type == u'ERROR'
        ).order_by(
            self.default_order
        ).all()

    def get_feed_messages(self, feed):
        return DBSession.query(Message).filter(
            Message.feed == feed
        ).order_by(
            self.default_order
        ).all()
