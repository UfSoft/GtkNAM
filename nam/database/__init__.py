# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
"""
    nam.database
    ~~~~~~~~~~~~~~~~~~~~~

    This module is a layer on top of SQLAlchemy to provide asynchronous
    access to the database and has the used tables/models used in the
    application

    :copyright: © 2010 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
    :license: BSD, see LICENSE for more details.
"""

import os
import sys
import logging
from os import path
from datetime import datetime
from types import ModuleType
from uuid import uuid4

import sqlalchemy
from sqlalchemy import and_, or_
from sqlalchemy import orm
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.engine.url import make_url, URL

from nam.utils.crypto import gen_pwhash, check_pwhash

from twisted.python import log as twlog

log = logging.getLogger(__name__)

#: create a new module for all the database related functions and objects
sys.modules['nam.database.db'] = db = ModuleType('db')
key = value = mod = None
for mod in sqlalchemy, orm:
    for key, value in mod.__dict__.iteritems():
        if key in mod.__all__:
            setattr(db, key, value)
del key, mod, value
db.and_ = and_
db.or_ = or_
#del and_, or_

DeclarativeBase = declarative_base()
metadata = DeclarativeBase.metadata

db.metadata = metadata


class SchemaVersion(DeclarativeBase):
    """SQLAlchemy-Migrate schema version control table."""

    __tablename__   = 'migrate_version'
    repository_id   = db.Column(db.String(255), primary_key=True)
    repository_path = db.Column(db.Text)
    version         = db.Column(db.Integer)

    def __init__(self, repository_id, repository_path, version):
        self.repository_id = repository_id
        self.repository_path = repository_path
        self.version = version


AUTH_LEVEL_NONE = 0
AUTH_LEVEL_READONLY = 1
AUTH_LEVEL_NORMAL = 5
AUTH_LEVEL_ADMIN = 10
AUTH_LEVEL_DEFAULT = AUTH_LEVEL_NORMAL

class User(DeclarativeBase):
    """Repositories users table"""
    __tablename__ = 'accounts'

    username        = db.Column(db.String, primary_key=True)
    display_name    = db.Column(db.String(50))
    password_hash   = db.Column(db.String, default="!")
    added_on        = db.Column(db.DateTime, default=datetime.utcnow)
    last_login      = db.Column(db.DateTime, default=datetime.utcnow)
    access_level    = db.Column(db.Integer, default=AUTH_LEVEL_NORMAL)

    def __init__(self, username=None, display_name=None, password=None,
                 access_level=AUTH_LEVEL_NORMAL):
        self.username = username
        self.display_name = display_name
        if password:
            self.set_password(password)
        self.access_level = access_level

    def set_password(self, password):
        self.password_hash = gen_pwhash(password)

    def check_password(self, password):
        if self.password_hash == '!':
            return False
        if check_pwhash(self.password_hash, password):
            self.last_login = datetime.utcnow()
            return True
        return False

    def __repr__(self):
        return '<User username=%s, access_level=%d>' % (self.username,
                                                        self.access_level)

class Source(DeclarativeBase):
    __tablename__   = 'sources'

    id              = db.Column(db.Integer, primary_key=True)
    uri             = db.Column(db.String)
    name            = db.Column(db.String)
    enabled         = db.Column(db.Boolean, default=True)
    buffer_size     = db.Column(db.Float, default=1)    # 1 Mb buffer
    buffer_duration = db.Column(db.Float, default=3)    # 3 secs buffer

    # Relations
    silence_checker = db.relation("SilenceCheckerProperties", backref="source",
                                  uselist=False, lazy=False)

    def __init__(self, uri, name, enabled=True, buffer_size=1, buffer_duration=3):
        self.uri = uri
        self.name = name
        self.enabled = enabled
        self.buffer_size = buffer_size
        self.buffer_duration = buffer_duration

    def to_dict(self):
        return {
            'id': self.id,
            'uri': self.uri,
            'name': self.name,
            'enabled': self.enabled,
            'buffer_size': self.buffer_size,
            'buffer_duration': self.buffer_duration
        }


class SilenceCheckerProperties(DeclarativeBase):
    __tablename__   = 'silence_checkers_properties'

    source_id       = db.Column(db.ForeignKey("sources.id"), primary_key=True)
    min_tolerance   = db.Column(db.Integer, default="2")
    max_tolerance   = db.Column(db.Integer, default="5")
    silence_level   = db.Column(db.Float, default=-65)

    def __init__(self, source_id):
        self.source_id = source_id

    def to_dict(self):
        return {
            "source_id": self.source_id,
            "min_tolerance": self.min_tolerance,
            "max_tolerance": self.max_tolerance,
            "silence_level": self.silence_level
        }


class MessageKind(DeclarativeBase):
    __tablename__   = 'message_kinds'

    id              = db.Column(db.Integer, primary_key=True)
    kind            = db.Column(db.String)


class Messages(DeclarativeBase):
    __tablename__   = 'messages'

    id              = db.Column(db.Integer, primary_key=True)
    stamp           = db.Column(db.DateTime, default=datetime.utcnow)
    source          = db.Column(db.ForeignKey('sources.id'))
    kind            = db.Column(db.ForeignKey('message_kinds.id'))
    message         = db.Column(db.String)

