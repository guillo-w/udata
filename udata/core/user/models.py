# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime
from time import time

from blinker import Signal
from flask import url_for, g, current_app
from flask.ext.security import UserMixin, RoleMixin, MongoEngineUserDatastore
from mongoengine.signals import pre_save, post_save
from itsdangerous import JSONWebSignatureSerializer

from werkzeug import cached_property

from udata.models import db, WithMetrics, Follow
from udata.core.storages import avatars, default_image_basename


__all__ = ('User', 'Role', 'datastore', 'FollowUser')


# def populate_slug(user):
#     return ' '.join([user.first_name, user.last_name])

AVATAR_SIZES = [100, 32, 25]


def upload_avatar_to(user):
    return '/'.join((user.slug, datetime.now().strftime('%Y%m%d-%H%M%S')))


# TODO: use simple text for role
class Role(db.Document, RoleMixin):
    ADMIN = 'admin'
    name = db.StringField(max_length=80, unique=True)
    description = db.StringField(max_length=255)

    def __str__(self):
        return self.name

    __unicode__ = __str__


class UserSettings(db.EmbeddedDocument):
    prefered_language = db.StringField()


class User(db.Document, WithMetrics, UserMixin):
    slug = db.SlugField(max_length=255, required=True, populate_from='fullname')
    email = db.StringField(max_length=255, required=True)
    password = db.StringField()
    active = db.BooleanField()
    roles = db.ListField(db.ReferenceField(Role), default=[])

    first_name = db.StringField(max_length=255, required=True)
    last_name = db.StringField(max_length=255, required=True)

    avatar_url = db.URLField()
    avatar = db.ImageField(fs=avatars, basename=default_image_basename, thumbnails=AVATAR_SIZES)
    website = db.URLField()
    about = db.StringField()

    prefered_language = db.StringField()

    apikey = db.StringField()

    created_at = db.DateTimeField(default=datetime.now, required=True)
    confirmed_at = db.DateTimeField()
    last_login_at = db.DateTimeField()
    current_login_at = db.DateTimeField()
    last_login_ip = db.StringField()
    current_login_ip = db.StringField()
    login_count = db.IntField()

    deleted = db.DateTimeField()
    ext = db.MapField(db.GenericEmbeddedDocumentField())
    extras = db.ExtrasField()

    before_save = Signal()
    after_save = Signal()
    on_create = Signal()
    on_update = Signal()
    before_delete = Signal()
    after_delete = Signal()
    on_delete = Signal()

    meta = {
        'allow_inheritance': True,
        'indexes': ['-created_at', 'slug', 'apikey'],
        'ordering': ['-created_at']
    }

    def __str__(self):
        return self.fullname

    __unicode__ = __str__

    @property
    def fullname(self):
        return ' '.join((self.first_name or '', self.last_name or '')).strip()

    @cached_property
    def organizations(self):
        from udata.core.organization.models import Organization
        return Organization.objects(members__user=self)

    @property
    def sysadmin(self):
        return bool(getattr(g, 'sysadmin'))

    @property
    def display_url(self):
        return url_for('users.show', user=self)

    @property
    def visible(self):
        return self.metrics.get('datasets', 0) + self.metrics.get('reuses', 0) > 0

    def generate_api_key(self):
        s = JSONWebSignatureSerializer(current_app.config['SECRET_KEY'])
        self.apikey = s.dumps({
            'user': str(self.id),
            'time': time(),
        })

    def clear_api_key(self):
        self.apikey = None

    @classmethod
    def get(cls, id_or_slug):
        obj = cls.objects(slug=id_or_slug).first()
        return obj or cls.objects.get_or_404(id=id_or_slug)

    @classmethod
    def pre_save(cls, sender, document, **kwargs):
        cls.before_save.send(document)

    @classmethod
    def post_save(cls, sender, document, **kwargs):
        cls.after_save.send(document)
        if kwargs.get('created'):
            cls.on_create.send(document)
        else:
            cls.on_update.send(document)


datastore = MongoEngineUserDatastore(db, User, Role)


pre_save.connect(User.pre_save, sender=User)
post_save.connect(User.post_save, sender=User)


class FollowUser(Follow):
    following = db.ReferenceField(User)
