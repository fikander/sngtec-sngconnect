from pyramid_mailer import get_mailer
from pyramid_mailer.message import Message as EmailMessage

from sngconnect.services.base import ServiceBase
from sngconnect.cassandra.notifications import Notifications
from sngconnect.database import DBSession, User, FeedUser

class NotificationService(ServiceBase):

    def __init__(self, *args, **kwargs):
        super(NotificationService, self).__init__(*args, **kwargs)
        self.mailer = get_mailer(self.request)
        self.notifications = Notifications()
        self.email_sender = self.request.registry['settings']['mail.sender']
        self.email_template = self.request.registry[
            'jinja2_environment'
        ].get_template(
            'sngconnect:templates/notification/emails/notification.txt'
        )

    def notify_all(self, summary, message):
        users = DBSession.query(User).all()
        self._notify(users, summary, message)

    def notify_feed_users(self, feed, summary, message):
        users = DBSession.query(User).join(
            FeedUser
        ).filter(
            FeedUser.feed == feed,
            FeedUser.role_user == True
        ).all()
        self._notify(users, summary, message)

    def mark_as_read(self, user, messages):
        self.notifications.set_read(
            user.id,
            [message.id for message in messages]
        )

    def get_unread_message_ids(self, user):
        return self.notifications.get_unread(user.id)

    def _notify(self, users, summary, message):
        self.notifications.set_unread(
            [user.id for user in users],
            message.id
        )
        for user in users:
            email = EmailMessage(
                subject=summary,
                sender=self.email_sender,
                recipients=[user.email],
                body=self.email_template.render(
                    user={
                        'id': user.id,
                    },
                    summary=summary,
                    message=message
                )
            )
            self.mailer.send(email)
