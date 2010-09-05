'''
Created on 23 Aug 2010

@author: vampas
'''

import logging
from twisted.internet import reactor
from nam import component
from nam.core import source
from nam.database import Source
from nam.event import *

log = logging.getLogger(__name__)

class SourcesManager(component.Component):
    def __init__(self):
        component.Component.__init__(self, "SourcesManager",
                                     depend=["DatabaseManager"])
        self.sources = {}

    def start(self):
        self.db = component.get("DatabaseManager")
        self.load_sources_from_db()

        for source_id in self.sources.keys():
            reactor.callLater(0, self.sources[source_id].start)

    def pause(self):
        pass

    def stop(self):
        for source_id in self.sources.keys():
            reactor.callLater(0, self.sources[source_id].stop)
            self.sources.pop(source_id)

    def shutdown(self):
        pass

    def load_sources_from_db(self):
        session = self.db.session()
        for item in session.query(Source).all():
            self.sources[item.id] = source.Source(item)
            component.get("EventManager").emit(SourceLoaded(item.id))

    def add_source(self, name, uri):
        session = component.get("DatabaseManager").session()
        if session.query(Source).filter_by(name=name).count() > 0:
            component.get("EventManager").emit(SourceExists(
                "A source with the name \"%s\" already exists. " % name +
                "Please choose another name.")
            )
        elif session.query(Source).filter_by(uri=uri).count() > 0:
            component.get("EventManager").emit(SourceExists(
                "A source with the uri \"%s\" already exists. " % uri +
                "Please choose another uri.")
            )
        source = Source(uri, name)
        session.add(source)
        session.commit()
        component.get("EventManager").emit(SourceAdded(source.id, source.to_dict()))

    def remove_source(self, id):
        pass

    def alter_source(self, id, name, uri):
        pass

    def get_sources_list(self, disabled=False):
        sources = []
        for source in self.sources.itervalues():
            if not disabled and not source.src_enabled:
                continue
            sources.append(source.get_details())
        return sources

    def __getitem__(self, source_id):
        return self.sources[source_id]
    get = get_source = __getitem__

    def get_source_details(self, source_id):
        return self.get_source(source_id).get_details()

