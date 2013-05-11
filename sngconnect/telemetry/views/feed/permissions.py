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
        if not self.feed_permissions['can_change_permissions']:
            raise httpexceptions.HTTPForbidden()
        if self.feed_user is None:
            self.can_manage_users = True
        else:
            self.can_manage_users = self.feed_user.role_user
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
                        FeedUser.user_id == user.id,
                        FeedUser.role_user == True
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
                            role_user=True
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
                        FeedUser.user_id == user.id,
                        FeedUser.role_maintainer == True
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
                        feed_user = FeedUser(
                            user_id=user.id,
                            feed_id=self.feed.id,
                            role_maintainer=True
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
        base_query = DBSession.query(FeedUser).join(User).options(
            joinedload(FeedUser.user)
        ).filter(
            FeedUser.feed_id == self.feed.id
        ).order_by(User.email)
        feed_users = base_query.filter(
            FeedUser.role_user == True
        ).all()
        feed_maintainers = base_query.filter(
            FeedUser.role_maintainer == True
        ).all()
        self.context.update({
            'feed_users': feed_users,
            'feed_maintainers': feed_maintainers,
            'add_user_form': add_user_form,
            'add_maintainer_form': add_maintainer_form,
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
        post_keys = filter(
            lambda x: x.startswith('can_access-'),
            self.request.POST.iterkeys()
        )
        feed_user_ids = []
        for post_key in post_keys:
            try:
                feed_user_ids.append(int(post_key.split('-')[1]))
            except (IndexError, ValueError):
                continue
        DBSession.query(FeedUser).filter(
            FeedUser.feed == self.feed,
            ~FeedUser.id.in_(feed_user_ids),
            FeedUser.user_id != self.user_id,
            FeedUser.role_user == True
        ).delete(synchronize_session=False)
        permission_fields = {
            'can_change_permissions': filter(
                lambda x: x.startswith('can_change_permissions-'),
                self.request.POST.iterkeys()
            ),
        }
        for field_name, post_keys in permission_fields.iteritems():
            feed_user_ids = []
            for post_key in post_keys:
                try:
                    feed_user_ids.append(int(post_key.split('-')[1]))
                except (IndexError, ValueError):
                    continue
            DBSession.query(FeedUser).filter(
                FeedUser.feed == self.feed,
                FeedUser.user_id != self.user_id,
                FeedUser.role_user == True
            ).update({
                field_name: False
            })
            DBSession.query(FeedUser).filter(
                FeedUser.feed == self.feed,
                FeedUser.id.in_(feed_user_ids),
                FeedUser.user_id != self.user_id,
                FeedUser.role_user == True
            ).update({
                field_name: True
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
            'sngconnect.telemetry.feed_permissions.set_maintainer_permissions'
        ),
        request_method='POST',
        permission='sngconnect.telemetry.access'
    )
    def set_maintainer_permissions(self):
        post_keys = filter(
            lambda x: x.startswith('can_access-'),
            self.request.POST.iterkeys()
        )
        feed_user_ids = []
        for post_key in post_keys:
            try:
                feed_user_ids.append(int(post_key.split('-')[1]))
            except (IndexError, ValueError):
                continue
        DBSession.query(FeedUser).filter(
            FeedUser.feed == self.feed,
            ~FeedUser.id.in_(feed_user_ids),
            FeedUser.user_id != self.user_id,
            FeedUser.role_maintainer == True
        ).delete(synchronize_session=False)
        permission_fields = {
            'can_change_permissions': filter(
                lambda x: x.startswith('can_change_permissions-'),
                self.request.POST.iterkeys()
            ),
        }
        for field_name, post_keys in permission_fields.iteritems():
            feed_user_ids = []
            for post_key in post_keys:
                try:
                    feed_user_ids.append(int(post_key.split('-')[1]))
                except (IndexError, ValueError):
                    continue
            DBSession.query(FeedUser).filter(
                FeedUser.feed == self.feed,
                FeedUser.user_id != self.user_id,
                FeedUser.role_maintainer == True
            ).update({
                field_name: False
            })
            DBSession.query(FeedUser).filter(
                FeedUser.feed == self.feed,
                FeedUser.id.in_(feed_user_ids),
                FeedUser.user_id != self.user_id,
                FeedUser.role_maintainer == True
            ).update({
                field_name: True
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
