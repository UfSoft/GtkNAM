'''
Created on 27 Aug 2010

@author: vampas
'''

# http://jokosher.python-hosting.com/file/JonoEdit/trunk/

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

#from twisted.python import threadable
#threadable.init()

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
#        self.src_id = source.id
#        self.src_uri = source.uri
#        self.source_name = source.name
#        self.source_enabled = source.enabled
        self.gst_setup_complete = False
        self.evtm = component.get("EventManager")
        self.used_element_names = []
        self.buffer_percent = 0
        self.status = STATUS_NONE
        self.running = STATUS_NONE

    def setup(self):
        if self.gst_setup_complete:
            return
        self.pipeline = gst.Pipeline("pipeline-%d" % self.src_id)
        self.pipeline.set_property("async-handling", True)
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message::buffering',
                         self.check_bus_buffering_messages)
#        self.bus.add_watch(self.onBusMessage)

        self.source = self.gst_element_factory_make('uridecodebin')
        self.source.set_property('uri', self.src_uri)
#        self.source.set_property('use-buffering', True)
#        self.source.set_property('download', True)
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
#        reactor.callLater(1, self.evtm.emit, SourcePlay(self.src_id))

#        reactor.callLater(6, self.evtm.emit, SourcePause(self.src_id))
#        reactor.callLater(8, self.add_autosink)
#        reactor.callLater(10, self.evtm.emit, SourcePlay(self.src_id))

    def stop(self):
        if not self.src_enabled:
            return
        self.silence.stop()
        self.evtm.emit(SourceStop(self.src_id))
        self.evtm.deregister_event_handler("SourcePlay", self.start_play)
        self.evtm.deregister_event_handler("SourcePause", self.pause_play)
        self.evtm.deregister_event_handler("SourceStop", self.stop_play)

    def shutdown(self):
        self.silence.shutdown()

    def set_status(self, status):
        self.status = status

    def start_play(self, source_id):
        if source_id == self.src_id:
            ret, state, pending = self.pipeline.get_state(0)
#            self.pipe2.set_state(gst.STATE_PLAYING)
            if state is not gst.STATE_PLAYING:
                log.debug("Source \"%s\" PLAYING. Current state: %s; Next State: %s",
                          self.src_name, state, pending)
                self.silence.start()
                self.pipeline.set_state(gst.STATE_PLAYING)
                self.evtm.emit(SourcePlaying(self.src_id))
                self.status = STATUS_OK
                self.running = STATUS_PLAY

    def stop_play(self, source_id):
        if source_id == self.src_id:
            ret, state, pending = self.pipeline.get_state(0)
            if state is not gst.STATE_NULL:
                log.debug("Source \"%s\" STOPPING. Current state: %s; Next State: %s",
                          self.src_name, state, pending)
                self.pipeline.set_state(gst.STATE_NULL)
                self.evtm.emit(SourceStopped(self.src_id))
                self.status = STATUS_NONE
                self.running = STATUS_STOP
                self.buffer_percent = 0
                self.silence.stop()

    def pause_play(self, source_id):
        if source_id == self.src_id:
            ret, state, pending = self.pipeline.get_state(0)
            if state not in (gst.STATE_PAUSED, gst.STATE_READY):
                log.debug("Source \"%s\" PAUSING. Current state: %s; Next State: %s",
                          self.src_name, state, pending)
                self.pipeline.set_state(gst.STATE_PAUSED)
                self.evtm.emit(SourcePaused(self.src_id))
                self.status = STATUS_NONE
                self.running = STATUS_PAUSE
                self.buffer_percent = 0

    def onBusMessage(self, bus, message):
        log.debug("\nonBusMessage: %s\n", message.structure)
        if message.src == self.pipeline and message.type == gst.MESSAGE_EOS:
            log.debug("GOT EOS!!!!")
            reactor.stop()
        elif message.type == gst.MESSAGE_ERROR:
            log.debug("Got ERROR: %s", message.parse_error())
            reactor.stop()
        return True

    def on_no_more_pads(self, dbin):
        self.evtm.emit(SourcePlay(self.src_id))

    def gst_element_factory_make(self, gst_element_name, element_name=None):
        if not element_name:
            element_name = "%s-%d" % (gst_element_name, self.src_id)
            if element_name in self.used_element_names:
                n = 1
                while True:
                    element_name = "%s-%d-%d" % (gst_element_name,
                                                 self.src_id, n)
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
#            self.resample = self.gst_element_factory_make('audioresample')
#            self.pipeline.add(self.resample)

            self.tee = self.gst_element_factory_make('tee')
            self.pipeline.add(self.tee)

            self.queue = self.gst_element_factory_make('queue')
#            self.queue.set_property("max-size-time", 2*gst.NSECOND)
            self.pipeline.add(self.queue)

#            self.sink = self.gst_element_factory_make('alsasink')
#            self.sink = self.gst_element_factory_make('autoaudiosink')

            self.sink = self.gst_element_factory_make('fakesink')
            self.sink.set_property('sync', True)

            self.pipeline.add(self.sink)

            self.source.link(self.convert)
#            self.convert.link(self.resample)
            self.convert.link(self.tee)
#            self.resample.link(self.tee)
            self.tee.link(self.queue)
            self.queue.link(self.sink)

            #gst.debug_set_default_threshold(gst.LEVEL_DEBUG)

#            self.pipe2 = pipeline = gst.Pipeline("pipeline-%d.1" % self.src_id)
#
#            queue = self.gst_element_factory_make('queue')
#            queue.set_state(gst.STATE_PAUSED)
#            sink = self.gst_element_factory_make('alsasink')
#            sink.set_state(gst.STATE_PAUSED)
#            pipeline.add(queue, sink)
#            queue.link(pipeline)
#            self.tee.link(queue)
#            pipeline.set_state(gst.STATE_PAUSED)

#            queue = self.gst_element_factory_make('queue')
#            queue.set_state(gst.STATE_PAUSED)
#            sink = self.gst_element_factory_make('alsasink')
#            sink.set_state(gst.STATE_PAUSED)
#            self.pipeline.add(queue, sink)
#            queue.link(sink)
#            self.tee.link(queue)



            self.convert.set_state(gst.STATE_PAUSED)
#            self.resample.set_state(gst.STATE_PAUSED)
            self.tee.set_state(gst.STATE_PAUSED)
            self.queue.set_state(gst.STATE_PAUSED)
            self.sink.set_state(gst.STATE_PAUSED)

            log.debug(self.tee)

            self.silence.prepare()

#            def get_info():
#                log.debug(self.pipeline.get_state(0))
##                log.debug(self.pipe2.get_state(0))
#            from twisted.internet.task import LoopingCall
#            state_check = LoopingCall(get_info)
#            state_check.start(10)
        return True

    def add_autosink(self):
#        reactor.callLater(0, self.evtm.emit, SourcePause(self.src_id))
#        gst.debug_set_default_threshold(gst.LEVEL_DEBUG)
#        pad = self.tee.get_request_pad("src%d")
#        pad.set_blocked(True)
        import os
        dotfile1 = "/tmp/nam-1-debug-graph.dot"
        pngfile1 = "/tmp/nam-1-debug-graph.png"
        dotfile2 = "/tmp/nam-2-debug-graph.dot"
        pngfile2 = "/tmp/nam-2-debug-graph.png"
        try:
            os.remove(dotfile1)
        except:
            pass
        try:
            os.remove(dotfile2)
        except:
            pass

        try:
            os.remove(pngfile1)
        except:
            pass
        try:
            os.remove(pngfile2)
        except:
            pass

        os.environ["GST_DEBUG_DUMP_DOT_DIR"] = "/tmp"
        os.putenv('GST_DEBUG_DUMP_DIR_DIR', '/tmp')

        gst.DEBUG_BIN_TO_DOT_FILE(self.pipeline,
                                  gst.DEBUG_GRAPH_SHOW_ALL,
                                  "nam-1-debug-graph")
#        subprocess.call(["/usr/bin/dot", "-Tpng", "-o", pngfile1, dotfile1])
        os.system("/usr/bin/dot -Tpng -o"+ pngfile1 +" "+ dotfile1)

##        self.pipeline.set_state(gst.STATE_PAUSED)
#
#        log.debug("Adding Autosink. Current State: %s", self.pipeline.get_state(0))
#        queue = self.gst_element_factory_make('queue2')
#        queue.sync_state_with_parent()
##        queue.set_state(gst.STATE_PLAYING)
##        queue.set_state(gst.STATE_PAUSED)
##        queue.set_property("max-size-time", 2*ONE_SECOND_IN_NANOSECONDS)
##        queue.set_property("leaky", True)
##        resample = self.gst_element_factory_make('audioresample')
##        resample.set_state(gst.STATE_PAUSED)
#        sink = self.gst_element_factory_make('alsasink')
#        sink.sync_state_with_parent()
##        sink.set_state(gst.STATE_PLAYING)
##        sourcecaps = gst.Caps()
##        sourcecaps.append_structure(gst.Structure("audio/x-raw-float"))
##        sourcecaps.append_structure(gst.Structure("audio/x-raw-int"))
##        sink.set_property("caps", sourcecaps)
##        sink.set_state(gst.STATE_PAUSED)
#
##        sink.set_property('async', True)
#        sink.set_property('sync', False)
#        self.pipeline.add(queue, sink)
#        self.tee.link(queue)
#        queue.link(sink)
##        resample.link(sink)
#        log.debug("Added Autosink: %s", self.used_element_names)
##        queue.set_state(gst.STATE_PAUSED)
##        sink.set_state(gst.STATE_PAUSED)
##        queue.set_state(gst.STATE_PLAYING)
##        sink.set_state(gst.STATE_PLAYING)
##        log.debug("Autosink Playing")
#        sink.sync_state_with_parent()
#        pad.set_blocked(False)

        def write_image():
            gst.DEBUG_BIN_TO_DOT_FILE(self.pipeline,
                                      gst.DEBUG_GRAPH_SHOW_ALL,
                                      "nam-2-debug-graph")
            os.system("/usr/bin/dot -Tpng -o"+ pngfile2 +" "+ dotfile2)
        reactor.callLater(5, write_image)
        log.debug(self.pipeline.get_state(0))


    def check_bus_buffering_messages(self, bus, message):
        self.buffer_percent = message.structure['buffer-percent']
        log.trace("Source \"%s\" Buffer at %s%%", self.src_name, self.buffer_percent)
        self.evtm.emit(SourceBufferingEvent(self.src_id, self.buffer_percent))
        if self.buffer_percent == 100:
            self.evtm.emit(SourceBufferedEvent(self.src_id))
            self.evtm.emit(SourcePlay(self.src_id))
        elif self.buffer_percent <= 40:
            self.evtm.emit(SourcePause(self.src_id))

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
            'buffer_percent': self.buffer_percent
        }

        # http://gst.ufsoft.org/AFM/file/eb88c8c530ab/afm/sources.py

