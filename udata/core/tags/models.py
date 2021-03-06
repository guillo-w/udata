# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import logging

log = logging.getLogger(__name__)

from udata.models import db

__all__ = ('Tag', )


class Tag(db.Document):
    name = db.StringField(required=True, unique=True)
    counts = db.DictField()
    total = db.IntField(default=0)

    meta = {
        'indexes': ['name', '-total'],
        'ordering': ['-total', ],
    }

    def clean(self):
        self.total = sum(self.counts.values())
