'''
Created on 7 Sep 2010

@author: vampas
'''

import gst
import logging
import pkg_resources
from twisted.internet import reactor
from nam import component

log = logging.getLogger(__name__)

class AudioPlayer(component.Component):

    def __init__(self):
        component.Component.__init__(self, "AudioPlayer")

        self.glade = component.get("MainWindow").get_glade()
        self.stop_audio_alert_button = self.glade.get_widget("StopAudioAlertToolbutton")
        self.stop_audio_alert_button.connect("clicked", self.on_StopAudioAlertToolbutton_clicked)

        self.playing = False
        self.stop_timeout = reactor.callLater(10, lambda x: x)
        self.stop_timeout.cancel()
        self.gst_setup_complete = False

    def setup(self):
        if self.gst_setup_complete:
            return

        self.pipeline = gst.Pipeline("GtkUiAudioPlayer")
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message', self.on_bus_message)

        self.source_src = pkg_resources.resource_filename(
            "nam", "data/audio/alert.mp3"
        )
        self.source = gst.element_factory_make("uridecodebin")
        log.debug("Alert Audio File Path: %s", self.source_src)
        self.source.set_property("uri", "file://%s" % self.source_src)

        self.sourcecaps = gst.Caps()
        self.sourcecaps.append_structure(gst.Structure("audio/x-raw-float"))
        self.sourcecaps.append_structure(gst.Structure("audio/x-raw-int"))
        self.source.set_property("caps", self.sourcecaps)

        self.pipeline.add(self.source)
        self.source.connect("pad-added", self.on_pad_added)
        self.source.connect("no-more-pads", self.on_no_more_pads)
        self.pipeline.set_state(gst.STATE_PAUSED)
        self.source.set_state(gst.STATE_PAUSED)
#        self.gst_setup_complete = True

    def start(self):
        self.setup()

    def stop(self):
        pass

    def shutdown(self):
        pass

    def start_play(self):
        ret, state, pending = self.pipeline.get_state(0)
        if state is not gst.STATE_PLAYING:
            log.debug("Play Audio Alert")
            self.pipeline.set_state(gst.STATE_PLAYING)

    def pause_play(self):
        ret, state, pending = self.pipeline.get_state(0)
        if state not in (gst.STATE_PAUSED, gst.STATE_READY):
            log.debug("Pause Audio Alert")
            self.pipeline.set_state(gst.STATE_PAUSED)

    def stop_play(self, forced=False):
        ret, state, pending = self.pipeline.get_state(0)
        if state is not gst.STATE_NULL and self.playing:
            log.debug("Stop Audio Alert")
            if forced:
                self.pipeline.set_state(gst.STATE_NULL)
                self.stop_timeout.active() and self.stop_timeout.cancel()
            elif not self.stop_timeout.active():
                self.stop_timeout = reactor.callLater(
                    60, self.pipeline.set_state, gst.STATE_NULL
                )
#            self.pipeline.set_state(gst.STATE_NULL)
#            self.playing = False

    def on_no_more_pads(self, dbin):
        self.gst_setup_complete = True
        self.pipeline.set_state(gst.STATE_PAUSED)

    def on_pad_added(self, dbin, sink_pad):
#        if self.gst_setup_complete:
#            return
        c = sink_pad.get_caps().to_string()
        if c.startswith("audio/"):
            self.convert = gst.element_factory_make('audioconvert')
            self.pipeline.add(self.convert)
            self.sink = gst.element_factory_make('alsasink')
            self.pipeline.add(self.sink)
            self.source.link(self.convert)
            self.convert.link(self.sink)
            self.convert.set_state(gst.STATE_PAUSED)
            self.sink.set_state(gst.STATE_PAUSED)

    def on_bus_message(self, bus, message):
        if message.src != self.pipeline:
            log.error("Got bus message which is not ours")
            return
        if message.type == gst.MESSAGE_STATE_CHANGED:
            ret, state, pending = message.parse_state_changed()
            self.stop_audio_alert_button.set_sensitive(state==gst.STATE_PLAYING)
            self.playing = (state==gst.STATE_PLAYING)
#            if state == gst.STATE_PLAYING:
#                self.playing = True
#                self.stop_audio_alert_button.set_sensitive(True)
#            else:
#                self.stop_audio_alert_button.set_sensitive(False)
            log.debug("GST_MESSAGE_STATE_CHANGED. Returned: %s  Current: %s  "
                      "Pending: %s", gst.element_state_get_name(ret),
                      gst.element_state_get_name(state),
                      gst.element_state_get_name(pending))
#            print gst.element_state_get_name(state)

        elif message.src == self.pipeline and message.type == gst.MESSAGE_EOS:
            log.debug("GOT EOS!!!!")
            self.pipeline.seek_simple(gst.FORMAT_TIME, gst.SEEK_FLAG_FLUSH, 0)
        elif message.type == gst.MESSAGE_ERROR:
            log.debug("Got ERROR: %s", message.parse_error())
        else:
            log.debug("%s\nonBusMessage: %s  Type: %s\n", self.__class__.__name__,
                      message.structure, message.type)
        return True

    def on_StopAudioAlertToolbutton_clicked(self, widget):
        self.stop_play(forced=True)
        self.stop_audio_alert_button.set_sensitive(False)
