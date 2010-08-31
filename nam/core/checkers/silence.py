'''
Created on 29 Aug 2010

@author: vampas
'''

import gst
import logging
from twisted.internet import reactor
from nam import component
from nam.event import NAMEvent


class AudioSilenceEvent(NAMEvent):
    def __init__(self, source_id, level, msg, levels):
        self._args = [source_id, level, msg, levels]

log = logging.getLogger(__name__)

class SilenceChecker(component.Component):
    TRIGGER_OK_TIMEOUT = 1

    def __init__(self, source):
        component.Component.__init__(self, "SilenceChecker-%s" % source.id)

        for key, value in source.silence_checker.to_dict().iteritems():
            setattr(self, key, value)

        self.evtm = component.get("EventManager")
        self.used_element_names = []
        self.gst_setup_complete = False
        self.trigger_ok_both = reactor.callLater(10, lambda x: x)
        self.trigger_ok_both.cancel()
        self.trigger_warning_both = reactor.callLater(10, lambda x: x)
        self.trigger_warning_both.cancel()
        self.trigger_failure_both = reactor.callLater(10, lambda x: x)
        self.trigger_failure_both.cancel()

        self.trigger_ok_left = reactor.callLater(10, lambda x: x)
        self.trigger_ok_left.cancel()
        self.trigger_warning_left = reactor.callLater(10, lambda x: x)
        self.trigger_warning_left.cancel()
        self.trigger_failure_left = reactor.callLater(10, lambda x: x)
        self.trigger_failure_left.cancel()

        self.trigger_ok_right = reactor.callLater(10, lambda x: x)
        self.trigger_ok_right.cancel()
        self.trigger_warning_right = reactor.callLater(10, lambda x: x)
        self.trigger_warning_right.cancel()
        self.trigger_failure_right = reactor.callLater(10, lambda x: x)
        self.trigger_failure_right.cancel()
        self.audio_failure_both_persists = False
        self.audio_failure_left_persists = False
        self.audio_failure_right_persists = False
        self.audio_failure_both_persists_right_ok = False
        self.audio_failure_both_persists_left_ok = False

    def start(self):
        log.debug("%s component starting", self._component_name)
        self.evtm.register_event_handler("AudioSilenceEvent",
                                         self.on_audio_silence_detected)
#        self.prepare()
        pass

    def stop(self):
        log.debug("%s component stoping", self._component_name)
        self.prepare_reverse()

    def pause(self):
        log.debug("%s component pausing", self._component_name)
        pass

    def shutdown(self):
        log.debug("%s component shutdown", self._component_name)

    def prepare(self):
        log.debug("%s component prepare", self._component_name)
        if self.gst_setup_complete:
            return
        self.source = component.get("SourcesManager").get(self.source_id)

        self.pipeline = self.source.pipeline
        self.bus = self.pipeline.get_bus()
#        self.bus.add_signal_watch()
        self.bus.connect('message::element', self.check_bus_level_messages)
        self.tee = self.source.tee
        self.queue = self.gst_element_factory_make("queue")
        self.queue.set_state(gst.STATE_PAUSED)
        self.pipeline.add(self.queue)
        self.tee.link(self.queue)
        self.level = self.gst_element_factory_make("level")
        self.level.set_state(gst.STATE_PAUSED)
        self.pipeline.add(self.level)
        self.queue.link(self.level)
        self.sink = self.gst_element_factory_make("fakesink")
        self.sink.set_property('sync', True)
        self.sink.set_state(gst.STATE_PAUSED)
        self.pipeline.add(self.sink)
        self.level.link(self.sink)
        self.gst_setup_complete = True

        log.debug("%s component prepared", self._component_name)

#        def get_info():
#            log.debug("%s component level state: %s", self._component_name,
#                      self.level.get_state(0))
#            log.debug(self.pipeline.get_state(0))
##                log.debug(self.pipe2.get_state(0))
#        from twisted.internet.task import LoopingCall
#        state_check = LoopingCall(get_info)
#        state_check.start(10)

    def prepare_reverse(self):
        log.debug("%s component prepare reverse", self._component_name)
        if not self.gst_setup_complete:
            return
        self.gst_setup_complete = False

    def gst_element_factory_make(self, gst_element_name, element_name=None):
        return self.source.gst_element_factory_make(gst_element_name, element_name)
        if not element_name:
            element_name = "%s-%d" % (gst_element_name, self.source_id)
            if element_name in self.used_element_names:
                n = 1
                while True:
                    element_name = "%s-%d-%d" % (gst_element_name, self.source_id, n)
                    if element_name in self.used_element_names:
                        n += 1
                    else:
                        break
        self.used_element_names.append(element_name)
        return gst.element_factory_make(gst_element_name, element_name)

    def on_audio_silence_detected(self, source_id, level, msg, levels):
        if source_id == self.source_id:
            log.debug("SILENCE DETECTED - SRC ID: %s, LEVEL: %s, MSG: %s",
                      source_id, level, msg)

#    def trigger_audio_warning(self, msg):
#        self.evtm.emit(AudioSilenceEvent(self.source_id, "WARN", msg))
#        reactor.callLater(self.max_tolerance, self.trigger_audio_failure, msg)
#
#    def trigger_audio_failure(self, msg):
#        self.evtm.emit(AudioSilenceEvent(self.source_id, "Error", msg))

    def audio_warning_both(self, levels):
        self.trigger_ok_both.active() and self.trigger_ok_both.cancel()
        self.trigger_ok_left.active() and self.trigger_ok_left.cancel()
        self.trigger_ok_right.active() and self.trigger_ok_right.cancel()
        msg = "Audio Failure on Both Channels"
        self.evtm.emit(AudioSilenceEvent(self.source_id, "WARN", "Possible %s" % msg, levels))
        self.trigger_failure_both = reactor.callLater(
            self.max_tolerance, self.audio_failure_both, msg, levels
        )
    def audio_failure_both(self, msg, levels):
        self.evtm.emit(AudioSilenceEvent(self.source_id, "ERROR", msg, levels))
        self.audio_failure_both_persists = True
    def audio_ok_both(self, levels):
        msg = "Audio Resumed on Both channels"
        if self.trigger_failure_both.active() or \
           self.audio_failure_both_persists or \
           self.trigger_failure_left.active() or \
           self.audio_failure_left_persists or \
           self.trigger_failure_right.active() or \
           self.audio_failure_right_persists:
             self.evtm.emit(AudioSilenceEvent(self.source_id, "OK", msg, levels))
        self.audio_failure_both_persists = False
        self.audio_failure_left_persists = False
        self.audio_failure_right_persists = False
        self.audio_failure_both_persists_right_ok = False
        self.audio_failure_both_persists_left_ok = False
        self.trigger_warning_both.active() and self.trigger_warning_both.cancel()
        self.trigger_failure_both.active() and self.trigger_failure_both.cancel()
        self.trigger_warning_left.active() and self.trigger_warning_left.cancel()
        self.trigger_failure_left.active() and self.trigger_failure_left.cancel()
        self.trigger_warning_right.active() and self.trigger_warning_right.cancel()
        self.trigger_failure_right.active() and self.trigger_failure_right.cancel()

    def audio_warning_left(self, levels):
        self.trigger_ok_both.active() and self.trigger_ok_both.cancel()
        self.trigger_ok_left.active() and self.trigger_ok_left.cancel()
        self.trigger_ok_right.active() and self.trigger_ok_right.cancel()
        msg = "Audio Failure on Left Channel: %s" % levels
        self.evtm.emit(AudioSilenceEvent(self.source_id, "WARN", "Possible %s" % msg, levels))
        self.trigger_failure_left = reactor.callLater(
            self.max_tolerance, self.audio_failure_left, msg, levels
        )
    def audio_failure_left(self, msg, levels):
        self.evtm.emit(AudioSilenceEvent(self.source_id, "ERROR", msg, levels))
        self.audio_failure_left_persists = True
    def audio_ok_left(self, levels):
        msg = "Audio Resumed on Left channel: %s" % levels
        if self.trigger_failure_left.active() or \
           self.audio_failure_left_persists or \
           self.trigger_failure_both.active() or \
           self.audio_failure_both_persists:
            self.evtm.emit(AudioSilenceEvent(self.source_id, "OK", msg, levels))
        self.audio_failure_left_persists = False
        if self.audio_failure_both_persists:
            self.audio_failure_both_persists_left_ok = True
        self.trigger_warning_left.active() and self.trigger_warning_left.cancel()
        self.trigger_failure_left.active() and self.trigger_failure_left.cancel()

    def audio_warning_right(self, levels):
        self.trigger_ok_both.active() and self.trigger_ok_both.cancel()
        self.trigger_ok_left.active() and self.trigger_ok_left.cancel()
        self.trigger_ok_right.active() and self.trigger_ok_right.cancel()
        msg = "Audio Failure on Right Channel: %s" % levels
        self.evtm.emit(AudioSilenceEvent(self.source_id, "WARN", "Possible %s" % msg, levels))
        self.trigger_failure_right = reactor.callLater(
            self.max_tolerance, self.audio_failure_right, msg, levels
        )
    def audio_failure_right(self, msg, levels):
        self.evtm.emit(AudioSilenceEvent(self.source_id, "ERROR", msg, levels))
        self.audio_failure_right_persists = True
    def audio_ok_right(self, levels):
        msg = "Audio Resumed on Right channel: %s" % levels
        if self.trigger_failure_right.active() or \
           self.audio_failure_right_persists or \
           self.trigger_failure_both.active() or \
           self.audio_failure_both_persists:
            self.evtm.emit(AudioSilenceEvent(self.source_id, "OK", msg, levels))
        self.audio_failure_right_persists = False
        if self.audio_failure_both_persists:
            self.audio_failure_both_persists_right_ok = True
        self.trigger_warning_right.active() and self.trigger_warning_right.cancel()
        self.trigger_failure_right.active() and self.trigger_failure_right.cancel()

    def check_bus_level_messages(self, bus, message):
#        log.debug("%s component check_bus_level_messages", self._component_name)
        if message.structure.get_name() == 'level':
            rms_left, rms_right = message.structure['rms']
            log.trace("Source \"%s\" RMS Left: %s  RMS Right: %s",
                      self.source.src_name, rms_left, rms_right)
            if (rms_left  < self.silence_level) or (rms_right < self.silence_level):
                if (rms_left  < self.silence_level) and (rms_right < self.silence_level):
                    if not self.trigger_warning_both.active() and not \
                        self.trigger_failure_both.active() and not \
                        self.audio_failure_both_persists:
                        self.trigger_warning_both = reactor.callLater(
                            self.min_tolerance, self.audio_warning_both,
                            message.structure['rms'])
                elif rms_left < self.silence_level:
                    if not self.trigger_warning_left.active() and not \
                        self.trigger_failure_left.active() and not \
                        self.audio_failure_left_persists and not \
                        self.trigger_failure_both.active() and not \
                        self.audio_failure_both_persists:
                        self.trigger_warning_left = reactor.callLater(
                            self.min_tolerance, self.audio_warning_left,
                            message.structure['rms'])
                elif rms_right < self.silence_level:
                    if not self.trigger_warning_right.active() and not \
                        self.trigger_failure_right.active() and not \
                        self.audio_failure_right_persists and not \
                        self.trigger_failure_both.active() and not \
                        self.audio_failure_both_persists:
                        self.trigger_warning_right = reactor.callLater(
                            self.min_tolerance, self.audio_warning_right,
                            message.structure['rms'])

                if rms_left > self.silence_level:
#                    log.trace("TOLA: %s  TFLA: %s  AFLP: %s  TFBA: %s  AFBP: %s",
#                              self.trigger_ok_left.active(),
#                              self.trigger_failure_left.active(),
#                              self.audio_failure_left_persists,
#                              self.trigger_failure_both.active(),
#                              self.audio_failure_both_persists)
                    if not self.trigger_ok_left.active() and not self.audio_failure_both_persists_left_ok:
                        if self.trigger_failure_left.active() or \
                           self.audio_failure_left_persists or \
                           self.trigger_failure_both.active() or \
                           self.audio_failure_both_persists:
                            self.trigger_ok_left = reactor.callLater(
                                self.TRIGGER_OK_TIMEOUT, self.audio_ok_left, message.structure['rms']
                            )
                    self.trigger_warning_left.active() and self.trigger_warning_left.cancel()
                elif rms_right > self.silence_level:
#                    log.trace("TORA: %s  TFRA: %s  AFRP: %s  TFBA: %s  AFBP: %s",
#                              self.trigger_ok_right.active(),
#                              self.trigger_failure_right.active(),
#                              self.audio_failure_right_persists,
#                              self.trigger_failure_both.active(),
#                              self.audio_failure_both_persists)
                    if not self.trigger_ok_right.active() and not self.audio_failure_both_persists_right_ok:
#                        log.trace("TFRA: %s  AFRP: %s  TFBA: %s  AFBP: %s",
#                                  self.trigger_failure_right.active(),
#                                  self.audio_failure_right_persists,
#                                  self.trigger_failure_both.active(),
#                                  self.audio_failure_both_persists)
                        if self.trigger_failure_right.active() or \
                           self.audio_failure_right_persists or \
                           self.trigger_failure_both.active() or \
                           self.audio_failure_both_persists:
                            self.trigger_ok_right = reactor.callLater(
                                self.TRIGGER_OK_TIMEOUT, self.audio_ok_right, message.structure['rms']
                            )
                    self.trigger_warning_right.active() and self.trigger_warning_right.cancel()
            elif (rms_left > self.silence_level) and (rms_right > self.silence_level):
#                log.trace("L and R > Silence")
                if (self.trigger_failure_both.active() and not self.trigger_ok_both.active()) or \
                   (self.audio_failure_both_persists and not self.trigger_ok_both.active()):
                    self.trigger_ok_both = reactor.callLater(
                        self.TRIGGER_OK_TIMEOUT, self.audio_ok_both, message.structure['rms']
                    )
                elif (self.trigger_failure_left.active() and not self.trigger_ok_left.active()) or \
                     (self.audio_failure_left_persists and not self.trigger_ok_left.active()):
                    self.trigger_ok_left = reactor.callLater(
                        self.TRIGGER_OK_TIMEOUT, self.audio_ok_left, message.structure['rms']
                    )
                elif (self.trigger_failure_right.active() and not self.trigger_ok_right.active()) or \
                     (self.audio_failure_right_persists and not self.trigger_ok_right.active()):
                    self.trigger_ok_right = reactor.callLater(
                        self.TRIGGER_OK_TIMEOUT, self.audio_ok_right, message.structure['rms']
                    )
                if self.trigger_warning_both.active() or \
                   self.trigger_warning_left.active() or \
                   self.trigger_warning_right.active():
                    self.trigger_warning_both.active() and self.trigger_warning_both.cancel()
                    self.trigger_warning_left.active() and self.trigger_warning_left.cancel()
                    self.trigger_warning_right.active() and self.trigger_warning_right.cancel()
#            elif (rms_left > self.silence_level) or (rms_right > self.silence_level):
#                log.trace("L or R > Silence")
#                if (rms_left > self.silence_level) and (rms_right > self.silence_level):
#                    log.trace("L and R > Silence")
#                    if (self.trigger_failure_both.active() and not self.trigger_ok_both.active()) or \
#                       (self.audio_failure_both_persists and not self.trigger_ok_both.active()):
#                        self.trigger_ok_both = reactor.callLater(
#                            self.TRIGGER_OK_TIMEOUT, self.audio_ok_both, message.structure['rms']
#                        )
#                    elif (self.trigger_failure_left.active() and not self.trigger_ok_left.active()) or \
#                         (self.audio_failure_left_persists and not self.trigger_ok_left.active()):
#                        self.trigger_ok_left = reactor.callLater(
#                            self.TRIGGER_OK_TIMEOUT, self.audio_ok_left, message.structure['rms']
#                        )
#                    elif (self.trigger_failure_right.active() and not self.trigger_ok_right.active()) or \
#                         (self.audio_failure_right_persists and not self.trigger_ok_right.active()):
#                        self.trigger_ok_right = reactor.callLater(
#                            self.TRIGGER_OK_TIMEOUT, self.audio_ok_right, message.structure['rms']
#                        )
#                    if self.trigger_warning_both.active() or \
#                       self.trigger_warning_left.active() or \
#                       self.trigger_warning_right.active():
#                        self.trigger_warning_both.active() and self.trigger_warning_both.cancel()
#                        self.trigger_warning_left.active() and self.trigger_warning_left.cancel()
#                        self.trigger_warning_right.active() and self.trigger_warning_right.cancel()
#                elif rms_left > self.silence_level:
#                    log.trace("TOLA: %s  TFLA: %s  AFLP: %s  TFBA: %s  AFBP: %s",
#                              self.trigger_ok_left.active(),
#                              self.trigger_failure_left.active(),
#                              self.audio_failure_left_persists,
#                              self.trigger_failure_both.active(),
#                              self.audio_failure_both_persists)
#                    if not self.trigger_ok_left.active():
#                        if self.trigger_failure_left.active() or \
#                           self.audio_failure_left_persists or \
#                           self.trigger_failure_both.active() or \
#                           self.audio_failure_both_persists:
#                            self.trigger_ok_left = reactor.callLater(
#                                self.TRIGGER_OK_TIMEOUT, self.audio_ok_left, message.structure['rms']
#                            )
#                    self.trigger_warning_left.active() and self.trigger_warning_left.cancel()
#                elif rms_right > self.silence_level:
#                    log.trace("TORA: %s  TFRA: %s  AFRP: %s  TFBA: %s  AFBP: %s",
#                              self.trigger_ok_right.active(),
#                              self.trigger_failure_right.active(),
#                              self.audio_failure_right_persists,
#                              self.trigger_failure_both.active(),
#                              self.audio_failure_both_persists)
#                    if not self.trigger_ok_right.active():
#                        log.trace("TFRA: %s  AFRP: %s  TFBA: %s  AFBP: %s",
#                                  self.trigger_failure_right.active(),
#                                  self.audio_failure_right_persists,
#                                  self.trigger_failure_both.active(),
#                                  self.audio_failure_both_persists)
#                        if self.trigger_failure_right.active() or \
#                           self.audio_failure_right_persists or \
#                           self.trigger_failure_both.active() or \
#                           self.audio_failure_both_persists:
#                            self.trigger_ok_right = reactor.callLater(
#                                self.TRIGGER_OK_TIMEOUT, self.audio_ok_right, message.structure['rms']
#                            )
#                    self.trigger_warning_right.active() and self.trigger_warning_right.cancel()
            else:
                log.debug("WHAT!!???: %s", message.structure['rms'])




