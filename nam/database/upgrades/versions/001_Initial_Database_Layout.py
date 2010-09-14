# -*- coding: utf-8 -*-
'''
Created on 23 Aug 2010

@author: vampas
'''
import os
import stat
import logging
from nam import configmanager
from nam.utils.crypto import gen_salt, gen_pwhash
from nam.database.upgrades.versions import *
DeclarativeBase = declarative_base()
metadata = DeclarativeBase.metadata

log = logging.getLogger('nam.database.upgrades.001')

class User(DeclarativeBase):
    """Repositories users table"""
    __tablename__ = 'accounts'

    username        = db.Column(db.String, primary_key=True)
    display_name    = db.Column(db.String(50))
    password_hash   = db.Column(db.String, default="!")
    added_on        = db.Column(db.DateTime, default=datetime.utcnow)
    last_login      = db.Column(db.DateTime, default=datetime.utcnow)
    access_level    = db.Column(db.Integer, default=10)

    def __init__(self, username=None, display_name=None, password=None,
                 access_level=10):
        self.username = username
        self.display_name = display_name
        if password:
            self.set_password(password)
        self.access_level = access_level

    def set_password(self, password):
        self.password_hash = gen_pwhash(password)

class Source(DeclarativeBase):
    __tablename__   = 'sources'

    id              = db.Column(db.Integer, primary_key=True)
    uri             = db.Column(db.String)
    name            = db.Column(db.String)
    enabled         = db.Column(db.Boolean, default=True)
    buffer_size     = db.Column(db.Float, default=1)    # 1 Mb buffer
    buffer_duration = db.Column(db.Float, default=3)    # 3 secs buffer

    def __init__(self, uri, name, enabled=True, buffer_size=1, buffer_duration=3):
        self.uri = uri
        self.name = name
        self.enabled = enabled
        self.buffer_size = buffer_size
        self.buffer_duration = buffer_duration

class SilenceCheckerProperties(DeclarativeBase):
    __tablename__   = 'silence_checkers_properties'

    source_id       = db.Column(db.ForeignKey("sources.id"), primary_key=True)
    min_tolerance   = db.Column(db.Integer, default=1)
    max_tolerance   = db.Column(db.Integer, default=4)
    silence_level   = db.Column(db.Float, default=-60)

    def __init__(self, source_id):
        self.source_id = source_id


class MessageKind(DeclarativeBase):
    __tablename__   = 'message_kinds'

    id              = db.Column(db.Integer, primary_key=True)
    kind            = db.Column(db.String)

    def __init__(self, kind):
        self.kind = kind


class Messages(DeclarativeBase):
    __tablename__   = 'messages'

    id              = db.Column(db.Integer, primary_key=True)
    stamp           = db.Column(db.DateTime, default=datetime.utcnow)
    source          = db.Column(db.ForeignKey('sources.id'))
    kind            = db.Column(db.ForeignKey('message_kinds.id'))
    message         = db.Column(db.String)


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; use the engine
    # named 'migrate_engine' imported from migrate.
    log.debug("Creating Database Tables")
    metadata.create_all(migrate_engine)

    log.debug("Creating local user")
    session = orm.create_session(migrate_engine, autoflush=True, autocommit=False)

    auth = configmanager.get_config_dir("auth")
    passwd = gen_salt(8)
    open(auth, "w").write(passwd+"\n")
    os.chmod(auth, stat.S_IREAD | stat.S_IWRITE)

    localuser = User('localuser', "Local User", passwd, 10)
    session.add(localuser)
    # Add Message Kinds
    for kind in ("ERROR", "WARNING", "OK"):
        session.add(MessageKind(kind))

    # Add default sources
    source = Source("mms://195.245.168.21/antena1", "Antena 1")
    session.add(source)
    checker = SilenceCheckerProperties(source.id)
    session.add(checker)

    source = Source("mms://195.245.168.21/antena2", "Antena 2")
    session.add(source)
    checker = SilenceCheckerProperties(source.id)
    checker.min_tolerance = 3
    checker.max_tolerance = 6
    session.add(checker)

    source = Source("mms://195.245.168.21/antena3", "Antena 3")
    session.add(source)
    checker = SilenceCheckerProperties(source.id)
    session.add(checker)

    source = Source("mms://195.245.168.21/rdpafrica", u"RDP África")
    session.add(source)
    checker = SilenceCheckerProperties(source.id)
    session.add(checker)

    source = Source("mms://195.245.168.21/rdpi", "RDP Internacional")
    session.add(source)
    checker = SilenceCheckerProperties(source.id)
    session.add(checker)

    source = Source("mms://195.245.168.21/radio3", u"Antena 1 Vida")
    session.add(source)
    checker = SilenceCheckerProperties(source.id)
    session.add(checker)

    source = Source("mms://195.245.168.21/lusitania", u"Rádio Lusitânia")
    session.add(source)
    checker = SilenceCheckerProperties(source.id)
    # A rádio lusitânia, estranhamente, quando não tem audio nenhum, continua
    # com ruído na ordem dos -40 dB's, demasiadamente alto, para um transporte
    # digital
    checker.silence_level = -43
    session.add(checker)

    source = Source("mms://195.245.168.21/radio4", u"Rádio República")
    session.add(source)
    checker = SilenceCheckerProperties(source.id)
    session.add(checker)

    source = Source("mms://195.245.168.21/radio5", u"Rádio Vivace")
    session.add(source)
    checker = SilenceCheckerProperties(source.id)
    session.add(checker)

    source = Source("mms://195.245.168.21/rdpmad", u"Antena 1 - Madeira")
    session.add(source)
    checker = SilenceCheckerProperties(source.id)
    session.add(checker)

    source = Source("mms://195.245.168.21/acores_a1", u"Antena 1 - Açores")
    session.add(source)
    checker = SilenceCheckerProperties(source.id)
    session.add(checker)

    source = Source("mms://195.245.168.21/ant3mad", u"Antena 3 - Madeira")
    session.add(source)
    checker = SilenceCheckerProperties(source.id)
    session.add(checker)

#    source = Source("file:///home/vampas/projects/GtkNAM/audio/FionaAudioSilenceTests.wav",
#                    "Fiona From File 1", enabled=False)
#    session.add(source)
#    checker = SilenceCheckerProperties(source.id)
#    session.add(checker)
#
#    source = Source("file:///home/vampas/projects/GtkNAM/audio/FionaAudioSilenceTests.wav",
#                    "Fiona From File 2", enabled=False)
#    session.add(source)
#    checker = SilenceCheckerProperties(source.id)
#    session.add(checker)
#
#    source = Source("file:///home/vampas/projects/GtkNAM/audio/FionaAudioSilenceTests.wav",
#                    "Fiona From File 3", enabled=False)
#    session.add(source)
#    checker = SilenceCheckerProperties(source.id)
#    session.add(checker)
#
#    source = Source("file:///home/vampas/projects/GtkNAM/audio/FionaAudioSilenceTests.wav",
#                    "Fiona From File 4", enabled=False)
#    session.add(source)
#    checker = SilenceCheckerProperties(source.id)
#    session.add(checker)
#
#    source = Source("file:///home/vampas/projects/GtkNAM/audio/FionaAudioSilenceTests.wav",
#                    "Fiona From File 5", enabled=False)
#    session.add(source)
#    checker = SilenceCheckerProperties(source.id)
#    session.add(checker)

    session.commit()


def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    metadata.drop_all(migrate_engine)
