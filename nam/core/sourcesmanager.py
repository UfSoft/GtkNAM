'''
Created on 23 Aug 2010

@author: vampas
'''

import logging
from twisted.internet import reactor
from nam import component
from nam.core import source
from nam.database import SilenceCheckerProperties, Source
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

        for idx, source_id in enumerate(self.sources.keys()):
            reactor.callLater(idx, self.start_source, source_id)

    def pause(self):

        for idx, source_id in enumerate(self.sources.keys()):
            reactor.callLater(idx, self.pause_source, source_id)

    def stop(self):
        for idx, source_id in enumerate(self.sources.keys()):
            reactor.callLater(idx, self.stop_source, source_id)
            self.sources.pop(source_id)

    def shutdown(self):
        pass

    def load_sources_from_db(self):
        session = self.db.session()
        for item in session.query(Source).all():
            self.sources[item.id] = source.Source(item)
            if item.enabled==True:
                self.sources[item.id].start()
            component.get("EventManager").emit(SourceLoaded(item.id))

    def add_source(self, name, uri, buffer_size, buffer_duration, enabled,
                   min_tolerance, max_tolerance, silence_level):
        session = component.get("DatabaseManager").session()
        if session.query(Source).filter_by(name=name).count() > 0:
            component.get("EventManager").emit(SourceExists(
                "A source with the name \"%s\" already exists. " % name +
                "Please choose another name.")
            )
            return
        elif session.query(Source).filter_by(uri=uri).count() > 0:
            component.get("EventManager").emit(SourceExists(
                "A source with the uri \"%s\" already exists. " % uri +
                "Please choose another uri.")
            )
            return
        log.info("Adding new audio source from %s with the name \"%s\"",
                 uri, name)
        new_source = Source(uri, name, enabled, buffer_size, buffer_duration)
        session.add(new_source)
        new_source.silence_checker = SilenceCheckerProperties(min_tolerance,
                                                              max_tolerance,
                                                              silence_level)
        session.commit()
        component.get("EventManager").emit(SourceAdded(new_source.id))
        if enabled:
            self.sources[new_source.id] = source.Source(new_source)
            self.sources[new_source.id].start()
            component.get("EventManager").emit(SourceLoaded(new_source.id))
#            component.get("Source-%s" % new_source.id).start()
#            component.get("EventManager").emit(SourcePlay(new_source.id))

    def remove_source(self, id):
        session = component.get("DatabaseManager").session()
        db_source = session.query(Source).get(id)
        if not db_source:
            component.get("EventManager").emit(SourceDoesNotExist(
                "A source by the id \"%s\" does not exist. " % id +
                "Something bad happened."))
            return
        component.deregister("Source-%s" % id)
        component.deregister("SilenceChecker-%s" % id)
        session.delete(db_source)
        session.commit()
        reactor.callLater(2, self.sources.pop, id)
        component.get("EventManager").emit(SourceRemoved(id))

    def alter_source(self, id, name, uri, buffer_size, buffer_duration, enabled,
                     min_tolerance, max_tolerance, silence_level):
        session = component.get("DatabaseManager").session()
        source = session.query(Source).get(id)
        if not source:
            component.get("EventManager").emit(SourceDoesNotExist(
                "A source by the id \"%s\" does not exist. " % id +
                "Something bad happened."))
            return

        name_query = session.query(Source).filter_by(name=name).first()
        if name_query != source and (name_query and name_query.name==name):
            component.get("EventManager").emit(SourceExists(
                "A source with the name \"%s\" already exists. " % name +
                "Please choose another name.")
            )
            return

        uri_query = session.query(Source).filter_by(uri=uri).first()
        if uri_query != source and (uri_query and uri_query==uri):
            component.get("EventManager").emit(SourceExists(
                "A source with the uri \"%s\" already exists. " % uri +
                "Please choose another uri.")
            )
            return

        source.name = name
        source.uri = uri
        source.buffer_size = buffer_size
        source.buffer_duration = buffer_duration
        source.enabled = enabled
        source.silence_checker.min_tolerance = min_tolerance
        source.silence_checker.max_tolerance = max_tolerance
        source.silence_checker.silence_level = silence_level
        session.commit()
        self.sources[source.id].update_details(source)
        component.get("EventManager").emit(SourceUpdated(id))

    def start_source(self, source_id):
#        self.sources[source_id].start()
        self.sources[source_id].start_play(source_id)
#        component.get("EventManager").emit(SourcePlay(source_id))

    def pause_source(self, source_id):
#        self.sources[source_id].pause()
#        component.get("EventManager").emit(SourcePause(source_id))
        self.sources[source_id].pause_play(source_id)

    def stop_source(self, source_id):
#        self.sources[source_id].stop()
#        component.get("EventManager").emit(SourceStop(source_id))
        self.sources[source_id].stop_play(source_id)

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

