import logging

from pyramid_mailer.interfaces import IMailer
from pyramid_mailer.message import Message as EmailMessage
from sqlalchemy.orm import joinedload

from sngconnect.services.base import ServiceBase
from sngconnect.services.sms import SMSService
from sngconnect.database import DBSession, User, FeedUser

logger = logging.getLogger(__name__)

class NotificationService(ServiceBase):

    _user_severity_flag_email = {
        'INFORMATION': 'send_email_info',
        'WARNING': 'send_email_warning',
        'ERROR': 'send_email_error',
        'COMMENT': 'send_email_comment',
        'ANNOUNCEMENT': 'send_email_info',
    }
    _user_severity_flag_sms = {
        'INFORMATION': 'send_sms_info',
        'WARNING': 'send_sms_warning',
        'ERROR': 'send_sms_error',
        'COMMENT': 'send_sms_comment',
        'ANNOUNCEMENT': 'send_sms_info',
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
        for user in users:
            try:
                self._send_email(user, summary, message)
            except:
                logger.exception(
                    "Unhandled exception while sending e-mail message."
                )
            try:
                self._send_sms(user, summary, message)
            except:
                logger.exception(
                    "Unhandled exception while sending SMS message."
                )

    def notify_feed_users(self, feed, summary, message):
        feed_users = DBSession.query(FeedUser).join(User).options(
            joinedload(FeedUser.user)
        ).filter(
            FeedUser.feed == feed
        )
        for feed_user in feed_users:
            permissions = feed_user.get_permissions()
            if 'email_notifications' in permissions:
                self._send_email(feed_user.user, summary, message)
            if 'sms_notifications' in permissions:
                self._send_sms(feed_user.user, summary, message)

    def _send_email(self, user, summary, message):
        if getattr(user, self._user_severity_flag_email[message.message_type]):
            mailer = self.registry.getUtility(IMailer)
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
            mailer.send(email)

    def _send_sms(self, user, summary, message):
        if (getattr(user, self._user_severity_flag_sms[message.message_type])
                and user.phone):
            sms_service = self.get_service(SMSService)
            try:
                sms_service.send_sms(
                    [user.phone],
                    summary
                )
            except sms_service.SendingError, e:
                logger.error(str(e))
