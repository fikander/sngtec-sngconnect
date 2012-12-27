import sqlalchemy as sql

from sngconnect.database import DBSession, Message

class MessageService(object):

    default_order = sql.desc(Message.date)

    @classmethod
    def create_message(cls, message):
        DBSession.add(message)

    @classmethod
    def get_important_messages(cls, feed):
        return DBSession.query(Message).filter(
            Message.feed == feed,
            Message.message_type == u'ERROR'
        ).order_by(
            cls.default_order
        ).all()

    @classmethod
    def get_feed_messages(cls, feed):
        return DBSession.query(Message).filter(
            Message.feed == feed
        ).order_by(
            cls.default_order
        ).all()
