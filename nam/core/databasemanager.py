'''
Created on 23 Aug 2010

@author: vampas
'''

import os
import logging
from os import path
import sqlalchemy
from sqlalchemy import orm
from sqlalchemy.engine.url import make_url, URL
from migrate.versioning.api import upgrade
from migrate.versioning.repository import Repository

from nam.database import upgrades, SchemaVersion, Source
import nam.component as component
import nam.configmanager as configmanager
from nam.event import (DatabaseUpgradeRequired, DatabaseUpgradeComplete,
                       DatabaseUpgradeStart)

log = logging.getLogger(__name__)

class DatabaseManager(component.Component):
    def __init__(self):
        component.Component.__init__(self, "DatabaseManager")

    def start(self):
        self.config = configmanager.ConfigManager("core.conf")
        self.create_engine()
        self.check_database()

    def stop(self):
        pass

    def shutdown(self):
        pass

    def create_engine(self):
        log.debug("Creating database engine")
        if self.config["db"]["engine"] == 'sqlite':
            info = URL('sqlite', database=path.join(self.config["db"]["path"],
                                                    self.config["db"]["name"]))
        else:
            if self.config["db"]["username"] and self.config["db"]["password"]:
                uri = '%(engine)s://%(username)s:%(password)s@%(host)s/%(name)s'
            if self.config["db"]["username"] and not self.config["db"]["password"]:
                uri = '%(engine)s://%(username)s@%(host)s/%(name)s'
            else:
                uri = '%(engine)s://%(host)s/%(name)s'
            info = make_url(uri % self.config["db"])
        if info.drivername == 'mysql':
            info.query.setdefault('charset', 'utf8')
        options = {'convert_unicode': True}
        # alternative pool sizes / recycle settings and more.  These are
        # interpreter wide and not from the config for the following reasons:
        #
        # - system administrators can set it independently from the webserver
        #   configuration via SetEnv and friends.
        # - this setting is deployment dependent should not affect a development
        #   server for the same instance or a development shell
        for key in 'pool_size', 'pool_recycle', 'pool_timeout':
            value = os.environ.get('NAM_DATABASE_' + key.upper())
            if value is not None:
                options[key] = int(value)
        self.engine = sqlalchemy.create_engine(info, **options)

    def check_database(self):
        if not self.engine.has_table(SchemaVersion.__tablename__):
            log.info("Creating database schema table")
            SchemaVersion.__table__.create(bind=self.engine)

        repository = Repository(upgrades.__path__[0])

        session = self.session()
        if not session.query(SchemaVersion).first():
            session.add(SchemaVersion(
                "Network Audio Monitor Schema Version Control",
                path.abspath(path.expanduser(repository.path)), 0)
            )
            session.commit()



        schema_version = session.query(SchemaVersion).first()
        if schema_version.version >= repository.latest:
            log.info("No database upgrade required")
            return
        component.get("EventManager").emit(DatabaseUpgradeRequired())
        log.warn("Upgrading database (from -> to...)")
        component.get("EventManager").emit(DatabaseUpgradeStart())
        upgrade(self.engine, repository)
        log.warn("Upgrade complete.")
        component.get("EventManager").emit(DatabaseUpgradeComplete())

    def session(self):
        return orm.create_session(self.engine, autoflush=True, autocommit=False)


