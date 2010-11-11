'''
Created on 27 Aug 2010

@author: vampas
'''

import logging
from nam import component
from nam.event import *
from nam.common import ftimenano, fsize
from nam.core.checkers.silence import SilenceChecker
import gst

# GST Debugging
gst.debug_set_active(True)
gst.debug_set_default_threshold(gst.LEVEL_WARNING)
#gst.debug_set_default_threshold(gst.LEVEL_INFO)
#gst.debug_set_default_threshold(gst.LEVEL_DEBUG)
gst.debug_set_colored(True)


from twisted.internet import reactor

log = logging.getLogger(__name__)

STATUS_ERROR, STATUS_WARNING, STATUS_OK, STATUS_NONE = range(4)
STATUS_PLAY, STATUS_PAUSE, STATUS_STOP = range(3)

class Source(component.Component):

    def __init__(self, source):
        component.Component.__init__(self, "Source-%d" % source.id)
        for key, value in source.to_dict().iteritems():
            setattr(self, "src_%s" % key, value)
        self.silence = SilenceChecker(source)
        self.gst_setup_complete = False
        self.evtm = component.get("EventManager")
        self.used_element_names = []
        self.buffer_percent = 0
        self.status = STATUS_NONE
        self.running = STATUS_NONE

    def __repr__(self):
        return self.__unicode__().encode('utf-8')

    def __unicode__(self):
        return u'<Source id="%d" name="%s">' % (self.src_id, self.src_name)

    def setup(self):
        if self.gst_setup_complete:
            return
        self.pipeline = gst.Pipeline("pipeline-%d" % self.src_id)
        self.pipeline.set_auto_flush_bus(False)
        self.pipeline.set_property("async-handling", True)
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message', self.on_bus_messages)

        self.source = self.gst_element_factory_make('uridecodebin')
        self.source.set_property('uri', self.src_uri)
        self.source.set_property('use-buffering', True)
        self.source.set_property('download', True)
        log.debug("Setting buffer-size on \"%s\" to %s", self.src_name,
                  fsize(self.src_buffer_size*1024*1024))
        self.source.set_property("buffer-size", self.src_buffer_size*1024*1024)
        log.debug("Setting buffer-duration on \"%s\" to %s", self.src_name,
                  ftimenano(self.src_buffer_duration*10e8))
        self.source.set_property("buffer-duration", self.src_buffer_duration*10e8)
        self.sourcecaps = gst.Caps()
        self.sourcecaps.append_structure(gst.Structure("audio/x-raw-float"))
        self.sourcecaps.append_structure(gst.Structure("audio/x-raw-int"))
        self.source.set_property("caps", self.sourcecaps)

        self.pipeline.add(self.source)
        self.source.connect("pad-added", self.on_pad_added)
        self.source.connect("no-more-pads", self.on_no_more_pads)
        self.pipeline.set_state(gst.STATE_PAUSED)
        self.source.set_state(gst.STATE_PAUSED)
        self.silence.start()
        self.gst_setup_complete = True
        self.running = STATUS_PAUSE

    def start(self):
        if not self.src_enabled:
            return
        log.debug("Starting Source \"%s\"", self.src_name)
        self.evtm.register_event_handler("SourcePlay", self.start_play)
        self.evtm.register_event_handler("SourcePause", self.pause_play)
        self.evtm.register_event_handler("SourceStop", self.stop_play)
        self.setup()

    def stop(self):
        log.debug("\n\nTrying to stop %s %s  enabled: %s\n\n",
                  self.src_id, self.src_name, self.src_enabled)
        if not self.src_enabled:
            return
        self.stop_play(self.src_id)
#        self.evtm.emit(SourceStop(self.src_id))
        self.evtm.deregister_event_handler("SourcePlay", self.start_play)
        self.evtm.deregister_event_handler("SourcePause", self.pause_play)
        self.evtm.deregister_event_handler("SourceStop", self.stop_play)

    def shutdown(self):
        self.silence.shutdown()

    def set_status(self, status):
        self.status = status

    def start_play(self, source_id):
        if source_id == self.src_id and self.src_enabled:
            self.setup()
            ret, state, pending = self.pipeline.get_state(0)
            if state is not gst.STATE_PLAYING:
                log.debug("Source \"%s\" PLAY. Returned: %s Current state: %s; Next State: %s",
                          self.src_name, ret, state, pending)
                self.pipeline.set_state(gst.STATE_PLAYING)


    def stop_play(self, source_id):
        if source_id == self.src_id and self.src_enabled:
            self.setup()
            ret, state, pending = self.pipeline.get_state(0)
            if state is not gst.STATE_NULL:
                log.debug("Source \"%s\" STOP. Returned: %s Current state: %s; Next State: %s",
                          self.src_name, ret, state, pending)
                self.pipeline.set_state(gst.STATE_NULL)
                self.revert_pipeline()

    def pause_play(self, source_id):
        if source_id == self.src_id and self.src_enabled:
            self.setup()
            ret, state, pending = self.pipeline.get_state(0)
            if state not in (gst.STATE_PAUSED, gst.STATE_READY):
#            if state is not gst.STATE_PAUSED:
                log.debug("Source \"%s\" PAUSE. Returned: %s Current state: %s; Next State: %s",
                          self.src_name, ret, state, pending)
                self.pipeline.set_state(gst.STATE_PAUSED)

    def on_no_more_pads(self, dbin):
        self.pause_play(self.src_id)
#        self.evtm.emit(SourcePause(self.src_id))

    def gst_element_factory_make(self, gst_element_name, element_name=None):
        if not element_name:
            element_name = "%s-%d" % (gst_element_name, self.src_id)
            if element_name in self.used_element_names:
                n = 1
                while True:
                    element_name = "%s-%d-%d" % (gst_element_name, self.src_id, n)
                    if element_name in self.used_element_names:
                        n += 1
                    else:
                        break
        self.used_element_names.append(element_name)
        return gst.element_factory_make(gst_element_name, element_name)

    def on_pad_added(self, dbin, sink_pad):
        c = sink_pad.get_caps().to_string()
        if c.startswith("audio/"):
            self.convert = self.gst_element_factory_make('audioconvert')
            self.pipeline.add(self.convert)

            self.tee = self.gst_element_factory_make('tee')
            self.pipeline.add(self.tee)

            self.queue = self.gst_element_factory_make('queue')
            self.pipeline.add(self.queue)

            self.sink = self.gst_element_factory_make('fakesink')
            self.sink.set_property('sync', True)

#            self.sink = self.gst_element_factory_make('alsasink')
#            self.sink.set_property('sync', True)

            self.pipeline.add(self.sink)

            self.source.link(self.convert)
            self.convert.link(self.tee)
            self.tee.link(self.queue)
            self.queue.link(self.sink)

            self.convert.set_state(gst.STATE_PAUSED)
            self.tee.set_state(gst.STATE_PAUSED)
            self.queue.set_state(gst.STATE_PAUSED)
            self.sink.set_state(gst.STATE_PAUSED)

            self.silence.prepare()
        return True

    def revert_pipeline(self):
        self.source.unlink(self.convert)
        self.convert.unlink(self.tee)
        self.tee.unlink(self.queue)
        self.queue.unlink(self.sink)
        self.pipeline.remove_many(self.convert, self.tee, self.queue, self.sink)
        self.silence.prepare_reverse()

    def get_details(self):
        return {
            'id': self.src_id,
            'uri': self.src_uri,
            'name': self.src_name,
            'status': self.status,
            'running': self.running,
            'enabled': self.src_enabled,
            'buffer_size': self.src_buffer_size,
            'buffer_duration': self.src_buffer_duration,
            'buffer_percent': self.buffer_percent,
            'silence': {
                'min_tolerance': self.silence.min_tolerance,
                'max_tolerance': self.silence.max_tolerance,
                'silence_level': self.silence.silence_level
            }
        }

    def update_details(self, source):
        self.setup()
        if self.src_name != source.name:
            log.debug("Source name changed from %s to %s",
                      self.src_name, source.name)
            self.src_name = source.name
        if source.uri != self.src_uri:
            log.debug("Source %s uri changed from %s to %s",
                      self.src_name, self.src_uri, source.uri)
            self.src_uri = source.uri
            self.source.set_property('uri', self.src_uri)
#            reactor.callLater(1, self.evtm.emit, SourceStop(self.src_id))
#            reactor.callLater(2, self.evtm.emit, SourcePlay(self.src_id))
            reactor.callLater(1, self.stop_play, self.src_id)
            reactor.callLater(2, self.start_play, self.src_id)
        if source.enabled != self.src_enabled:
            log.debug("Source %s enabled property changed from %s to %s",
                      self.src_name, self.src_enabled, source.enabled)
            if source.enabled:
                self.src_enabled = source.enabled
                self.start_play(self.src_id)
#                self.evtm.emit(SourcePlay(self.src_id))
            else:
                self.stop_play(self.src_id)
                self.src_enabled = source.enabled
#                self.evtm.emit(SourceStop(self.src_id))
        if source.buffer_size != self.src_buffer_size:
            log.debug("Source %s buffer size changed from %s to %s",
                      self.src_name, fsize(self.src_buffer_size*1024*1024),
                      fsize(source.buffer_size*1024*1024))
            self.src_buffer_size = source.buffer_size
            self.source.set_property("buffer-size",
                                     self.src_buffer_size*1024*1024)
        if source.buffer_duration == self.src_buffer_duration:
            log.debug("Source %s buffer duration changed from %s to %s",
                      self.src_name, ftimenano(self.src_buffer_duration*10e8),
                      ftimenano(source.buffer_duration*10e8))
            self.src_buffer_duration = source.buffer_duration
            self.source.set_property("buffer-duration",
                                     self.src_buffer_duration*10e8)

        self.silence.update_details(source.silence_checker)

    def on_bus_messages(self, bus, message):
        if message.type == gst.MESSAGE_STATE_CHANGED:
            ret, state, pending = message.parse_state_changed()
            def logit():
                log.trace("Source \"%s\" state changed. Current: %s",
                          self.src_name, state)
            if state == gst.STATE_PLAYING: # and self.running != STATUS_PLAY:
                logit()
                self.evtm.emit(SourcePlaying(self.src_id))
                self.status = STATUS_OK
                self.running = STATUS_PLAY
            elif state == gst.STATE_NULL: # and self.running != STATUS_STOP:
                logit()
                self.evtm.emit(SourceStopped(self.src_id))
                self.status = STATUS_NONE
                self.running = STATUS_STOP
                self.buffer_percent = 0
#                self.silence.stop()
            elif state == gst.STATE_PAUSED: # and self.running != STATUS_PAUSE:
                logit()
                self.evtm.emit(SourcePaused(self.src_id))
                self.status = STATUS_NONE
                self.running = STATUS_PAUSE
                self.buffer_percent = 0
#            elif state == gst.STATE_READY and self.running != STATUS_STOP:
#                self.evtm.emit(SourceStopped(self.src_id))
#                self.status = STATUS_NONE
#                self.running = STATUS_STOP
#                self.buffer_percent = 0
#            elif state == gst.STATE_VOID_PENDING:
#                self.pipeline.set_state(gst.STATE_NULL)
##                self.evtm.emit(SourceStopped(self.src_id))
#                self.status = STATUS_NONE
#                self.running = STATUS_STOP
#                self.buffer_percent = 0
#                self.silence.stop()

        elif message.type == gst.MESSAGE_BUFFERING:
            self.handle_buffering_message(bus, message)
        elif message.type == gst.MESSAGE_STREAM_STATUS:
            log.debug("\n\nMESSAGE_STREAM_STATUS(%s) - Structure: %s",
                      message.type, message.structure)
            log.debug("Parsed: %s\n\n", message.parse_stream_status())
        elif message.type == gst.MESSAGE_ELEMENT:
            if message.structure.get_name() == 'level':
                log.garbage("MESAGE ELEMENT Structure: %s [%s]",
                            message.structure, message.structure.get_name())
            elif message.structure.get_name() == 'redirect':
                log.debug("\n\nMESSAGE REDIRECT: %s\n\n", message.structure['redirect'])
                try:
                    log.debug("REDIRECT NEW LOCATION: %s\n\n", message.structure['new-location'])
                except:
                    pass
                reactor.callLater(15, reactor.stop)
            else:
                log.debug("MESAGE ELEMENT Structure: %s [%s]",
                          message.structure, message.structure.get_name())
        else:
            log.debug("Message Type: %s  Structure: %s",
                      message.type, message.structure)
        return True


    def handle_buffering_message(self, bus, message):
        self.buffer_percent = message.structure['buffer-percent']
        log.garbage("Source \"%s\" Buffer at %s%%", self.src_name,
                    self.buffer_percent)
        self.evtm.emit(SourceBufferingEvent(self.src_id, self.buffer_percent))
        if self.buffer_percent == 100:
            self.evtm.emit(SourceBufferedEvent(self.src_id))
            self.start_play(self.src_id)
#            self.evtm.emit(SourcePlay(self.src_id))
        else:
            if self.running != STATUS_PAUSE:
                self.pause_play(self.src_id)
#                self.evtm.emit(SourcePause(self.src_id))

    def handle_redirect_message(self, bus, message):
        log.debug("Got a redirect message")
        self.buffer_percent = message.structure['buffer-percent']
