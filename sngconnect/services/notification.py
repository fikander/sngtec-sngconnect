from pyramid_mailer.interfaces import IMailer
from pyramid_mailer.message import Message as EmailMessage

from sngconnect.services.base import ServiceBase
from sngconnect.database import DBSession, User, FeedUser

class NotificationService(ServiceBase):

    _user_severity_flag_email = {
        'INFORMATION': 'send_email_info',
        'WARNING': 'send_email_warning',
        'ERROR': 'send_email_error',
        'COMMENT': 'send_email_comment',
        'ANNOUNCEMENT': 'send_email_info',
    }

    def __init__(self, *args, **kwargs):
        super(NotificationService, self).__init__(*args, **kwargs)
        self.email_sender = self.registry['settings']['mail.sender']
        self.email_template = self.registry[
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

    def _notify(self, users, summary, message):
        for user in users:
            if not getattr(user, self._user_severity_flag_email[message.type]):
                continue
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
            self.registry.getUtility(IMailer).send(email)
