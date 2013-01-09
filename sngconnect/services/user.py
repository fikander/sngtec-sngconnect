import sqlalchemy as sql

from sngconnect.services.base import ServiceBase
from sngconnect.database import DBSession, User, FeedUser

class UserService(ServiceBase):

    default_order = sql.asc(User.email)

    def get_all_users(self, summary, message):
        return DBSession.query(User).order_by(
            self.default_order
        ).all()

    def get_all_feed_users(self, feed):
        return DBSession.query(User).join(
            FeedUser
        ).filter(
            FeedUser.feed == feed
        ).order_by(
            self.default_order
        ).all()
