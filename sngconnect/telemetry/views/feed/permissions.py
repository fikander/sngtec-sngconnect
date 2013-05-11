# -*- coding: utf-8 -*-

from sqlalchemy.orm import joinedload
from pyramid.view import view_config
from pyramid import httpexceptions

from sngconnect.translation import _
from sngconnect.database import DBSession, FeedUser, User
from sngconnect.telemetry import forms
from sngconnect.telemetry.views.feed.base import FeedViewBase

@view_config(
    route_name='sngconnect.telemetry.feed_permissions',
    renderer='sngconnect.telemetry:templates/feed/permissions.jinja2',
    permission='sngconnect.telemetry.access'
)
class FeedPermissions(FeedViewBase):

    def __init__(self, request):
        super(FeedPermissions, self).__init__(request)
        if 'access_permissions' not in self.feed_permissions:
            raise httpexceptions.HTTPForbidden()
        self.can_manage_users = 'manage_users' in self.feed_permissions
        self.context.update({
            'can_manage_users': self.can_manage_users,
        })

    def __call__(self):
        add_user_form = forms.AddFeedUserForm(
            csrf_context=self.request
        )
        add_maintainer_form = forms.AddFeedMaintainerForm(
            csrf_context=self.request
        )
        if self.request.method == 'POST':
            if 'submit_add_user' in self.request.POST:
                if not self.can_manage_users:
                    raise httpexceptions.HTTPForbidden()
                add_user_form.process(self.request.POST)
                if add_user_form.validate():
                    user = add_user_form.get_user()
                    feed_user_count = DBSession.query(FeedUser).filter(
                        FeedUser.feed == self.feed,
                        FeedUser.user_id == user.id
                    ).count()
                    if feed_user_count > 0:
                        add_user_form.email.errors.append(
                            _("This user already has access to this device.")
                        )
                    else:
                        DBSession.query(User).filter(
                            User.id == user.id,
                        ).update({
                            'role_user': True,
                        })
                        feed_user = FeedUser(
                            feed=self.feed,
                            user_id=user.id,
                            role='USER_STANDARD'
                        )
                        DBSession.add(feed_user)
                        self.request.session.flash(
                            _("User has been successfuly added."),
                            queue='success'
                        )
                        return httpexceptions.HTTPFound(
                            self.request.route_url(
                                'sngconnect.telemetry.feed_permissions',
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
            elif 'submit_add_maintainer' in self.request.POST:
                add_maintainer_form.process(self.request.POST)
                if add_maintainer_form.validate():
                    user = add_maintainer_form.get_user()
                    feed_user_count = DBSession.query(FeedUser).filter(
                        FeedUser.feed_id == self.feed.id,
                        FeedUser.user_id == user.id
                    ).count()
                    if feed_user_count > 0:
                        add_maintainer_form.email.errors.append(
                            _(
                                "This maintainer already has access to"
                                " this device."
                            )
                        )
                    else:
                        DBSession.query(User).filter(
                            User.id == user.id,
                        ).update({
                            'role_maintainer': True,
                        })
                        if self.feed_user.role_maintainer:
                            role = 'MAINTAINER_STANDARD'
                        else:
                            role = 'MAINTAINER_PLUS'
                        feed_user = FeedUser(
                            user_id=user.id,
                            feed_id=self.feed.id,
                            role=role
                        )
                        DBSession.add(feed_user)
                        self.request.session.flash(
                            _("Maintainer has been successfuly added."),
                            queue='success'
                        )
                        return httpexceptions.HTTPFound(
                            self.request.route_url(
                                'sngconnect.telemetry.feed_permissions',
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
        query = DBSession.query(FeedUser).join(User).options(
            joinedload(FeedUser.user)
        ).filter(
            FeedUser.feed == self.feed
        ).order_by(User.email)
        feed_users = []
        feed_maintainers = []
        for feed_user in query:
            if feed_user.role_user:
                feed_users.append(feed_user)
            elif feed_user.role_maintainer:
                feed_maintainers.append({
                    'feed_user': feed_user,
                    'revoke_access_form': forms.RevokeMaintainerAccessForm(
                        id=feed_user.id,
                        csrf_context=self.request,
                    ),
                })
            else:
                print "KASIAAAA", feed_user
        self.context.update({
            'feed_users': feed_users,
            'feed_maintainers': feed_maintainers,
            'add_user_form': add_user_form,
            'add_maintainer_form': add_maintainer_form,
            'revoke_maintainer_access_url': self.request.route_url(
                'sngconnect.telemetry.feed_permissions.revoke_maintainer_access',
                feed_id=self.feed.id
            ),
            'can_set_user_plus': 'manage_users_plus' in self.feed_permissions,
        })
        return self.context

    @view_config(
        route_name='sngconnect.telemetry.feed_permissions.set_user_permissions',
        request_method='POST',
        permission='sngconnect.telemetry.access'
    )
    def set_user_permissions(self):
        if not self.can_manage_users:
            raise httpexceptions.HTTPForbidden()
        post_items = filter(
            lambda x: x[0].startswith('role-'),
            self.request.POST.iteritems()
        )
        feed_user_roles = {}
        feed_users_to_delete = []
        for key, value in post_items:
            value = value.strip()
            try:
                id = int(key.split('-')[1])
            except (IndexError, ValueError):
                continue
            if value:
                feed_user_roles[id] = value
            else:
                feed_users_to_delete.append(id)
        DBSession.query(FeedUser).filter(
            FeedUser.feed == self.feed,
            FeedUser.id.in_(feed_users_to_delete),
            FeedUser.user_id != self.user_id
        ).delete(synchronize_session=False)
        for feed_user_id, role in feed_user_roles.iteritems():
            DBSession.query(FeedUser).filter(
                FeedUser.feed == self.feed,
                FeedUser.id == feed_user_id,
                FeedUser.user_id != self.user_id
            ).update({
                'role': role
            }, synchronize_session=False)
        self.request.session.flash(
            _("User permissions have been successfuly saved."),
            queue='success'
        )
        return httpexceptions.HTTPFound(
            self.request.route_url(
                'sngconnect.telemetry.feed_permissions',
                feed_id=self.feed.id
            )
        )

    @view_config(
        route_name=(
            'sngconnect.telemetry.feed_permissions.revoke_maintainer_access'
        ),
        request_method='POST',
        permission='sngconnect.telemetry.access'
    )
    def revoke_maintainer_access(self):
        form = forms.RevokeMaintainerAccessForm(csrf_context=self.request)
        form.process(self.request.POST)
        if not form.validate():
            raise httpexceptions.HTTPBadRequest()
        DBSession.query(FeedUser).filter(
            FeedUser.feed == self.feed,
            FeedUser.id == form.id.data,
            FeedUser.user_id != self.user_id
        ).delete(synchronize_session=False)
        self.request.session.flash(
            _("Maintainer access has have been successfuly revoked."),
            queue='success'
        )
        return httpexceptions.HTTPFound(
            self.request.route_url(
                'sngconnect.telemetry.feed_permissions',
                feed_id=self.feed.id
            )
        )
