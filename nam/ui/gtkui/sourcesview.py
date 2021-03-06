'''
Created on 2 Sep 2010

@author: vampas
'''

import gtk
import gtk.gdk
import pango
import gobject
from gtk import gdk
import logging

from twisted.internet import reactor, threads
from twisted.internet.task import LoopingCall

from nam import common, component
from nam.ui.client import client

log = logging.getLogger(__name__)

STATUS_PLAY, STATUS_PAUSE, STATUS_STOP, STATUS_NONE = range(4)


class SourceUI(gtk.VBox):
    __gtype_name__ = 'SourceUI'

    def __init__(self, source_id, name):
        gtk.VBox.__init__(self, False, 4)
        self.src_id = source_id
        self.src_name = name

        self.top = gtk.HBox(False, 0)
        self.pack_start(self.top, False, True, 2)
        self.top.show()

        self.label = gtk.Label()
        self.label.set_markup("<b>%s</b>" % self.src_name)
        self.label.set_alignment(0.0, 0.5)
        self.label.modify_font(pango.FontDescription("Verdana 8"))
        self.top.pack_start(self.label, expand=True, fill=True, padding=1)

        self.image = gtk.Image()
        self.top.pack_start(self.image, expand=False, fill=False, padding=1)
        self.error = gdk.pixbuf_new_from_file(common.get_pixmap("source-error.png"))
        self.warning = gdk.pixbuf_new_from_file(common.get_pixmap("source-warning.png"))

        self.bottom = gtk.HBox(False, 0)
        self.pack_start(self.bottom, expand=False, fill=True, padding=0)

        self.progress = gtk.ProgressBar()
        #self.progress.install_style_property("min-vertical-bar-height", 14)
        self.progress.modify_font(pango.FontDescription("Verdana 1"))
#        self.progress.install_style_property("yspacing", 0)
        self.progress_style = self.progress.get_style().copy()
        self.progress_style.yspacing = 0
        setattr(self.progress_style, "min-horizontal-bar-height", 40)
#        self.progress_style["min-horizontal-bar-height"] = 2
        self.progress.set_style(self.progress_style)
        self.progress_default_color = None
        #self.vbox.add(self.progress)
        self.bottom.pack_start(self.progress, expand=True, fill=True, padding=0)

        self.buttonbox = gtk.HButtonBox()
        self.buttonbox.set_layout(gtk.BUTTONBOX_START)
        self.buttonbox.set_spacing(1)
        self.buttonbox.set_child_size(28, 28)
#        self.bottom.pack_start(self.buttonbox, expand=False, fill=False, padding=1)
        self.top.pack_start(self.buttonbox, expand=False, fill=False, padding=1)
#        self.play = gtk.Button(label=None, stock=gtk.STOCK_MEDIA_PLAY)
        self.play = gtk.Button(label=None, stock=None, use_underline=False)
        self.play.connect("clicked", self.play_clicked)
        self.play.set_alignment(0.5, 0.5)
        self.play_image = gtk.Image()
        self.play_image.set_from_stock(gtk.STOCK_MEDIA_PLAY, gtk.ICON_SIZE_BUTTON)
        self.play.set_image(self.play_image)
        self.play.set_size_request(gtk.ICON_SIZE_BUTTON, gtk.ICON_SIZE_BUTTON)
#        self.buttonbox.add(self.play)
        self.buttonbox.pack_start(self.play, expand=False, fill=False)
#        self.stop = gtk.Button(label=None, stock=gtk.STOCK_MEDIA_STOP)

        self.pause = gtk.Button(label=None, stock=None, use_underline=False)
        self.pause.set_alignment(0.5, 0.5)
        self.pause_image = gtk.Image()
        self.pause_image.set_from_stock(gtk.STOCK_MEDIA_PAUSE, gtk.ICON_SIZE_BUTTON)
        self.pause.set_image(self.pause_image)
        self.pause.set_size_request(gtk.ICON_SIZE_BUTTON, gtk.ICON_SIZE_BUTTON)
        self.buttonbox.add(self.pause)
        self.buttonbox.pack_start(self.pause, expand=False, fill=False)

        self.stop = gtk.Button(label=None, stock=None, use_underline=False)
        self.stop.connect("clicked", self.stop_clicked)
        self.stop.set_alignment(0.5, 0.5)
        self.stop_image = gtk.Image()
        self.stop_image.set_from_stock(gtk.STOCK_MEDIA_STOP, gtk.ICON_SIZE_BUTTON)
        self.stop.set_image(self.stop_image)
        self.stop.set_size_request(gtk.ICON_SIZE_BUTTON, gtk.ICON_SIZE_BUTTON)
        self.buttonbox.add(self.stop)
        self.buttonbox.pack_start(self.stop, expand=False, fill=False)
        #self.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#ffffff"))

        self.separator = gtk.HSeparator()
        self.pack_start(self.separator, False, False, 2)
        self.separator.show()


    def update_progress(self, percentage):
        log.trace("Updatint percentage fraction: %s" % (percentage/100.0))
        if not self.progress_default_color:
            self.progress_style = progress_style = self.progress.get_style().copy()
            self.progress_default_color = progress_style.bg[gtk.STATE_PRELIGHT]

        if percentage < 100:
#            if percentage == 0:
#                self.progress.set_text("Buffer Empty")
#            else:
#                self.progress.set_text("Buffering %s%%" % percentage)
            if percentage < 40:
                progress_style = self.progress.get_style().copy()
                progress_style.bg[gtk.STATE_PRELIGHT] = gtk.gdk.color_parse("red")
                self.progress.set_style(progress_style)
            elif percentage < 60:
                progress_style = self.progress.get_style().copy()
                progress_style.bg[gtk.STATE_PRELIGHT] = gtk.gdk.color_parse("orange")
                self.progress.set_style(progress_style)
        else:
#            self.progress.set_text("Buffer Full")
            self.progress.set_style(None)

        self.progress.set_fraction(percentage/100.0)

    def set_status(self, status):
        if status >= 2:
            self.image.hide()
            component.get("AudioPlayer").stop_play()
#            self.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("white"))
        elif status == 1:
            self.image.set_from_pixbuf(self.warning)
            self.image.show()
#            self.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("orange"))
        else:
            self.image.set_from_pixbuf(self.error)
            self.image.show()
            component.get("AudioPlayer").start_play()

    def set_play_status(self, status):
        self.play.hide()
        self.pause.hide()
        self.stop.hide()
        if status >= 2:
            # Stopped Allow Play
#            reactor.callInThread(play_alert)
#            threads.deferToThread(play_alert)
#            component.get("AudioPlayer").start_play()
            self.play.show()
        elif status == 1:
            # Currently Paused, Allow Stop
#            reactor.callInThread(play_alert)
#            threads.deferToThread(play_alert)
#            component.get("AudioPlayer").start_play()
            self.play.show()
        else:
            # Currently Playing, Allow Stop
            self.stop.show()
#            reactor.callInThread(play_alert)

    def play_clicked(self, widget):
        client.core.play_source(self.src_id)

    def stop_clicked(self, widget):
        client.core.stop_source(self.src_id)

gobject.type_register(SourceUI)


class SourcesView(component.Component):
    def __init__(self):
        component.Component.__init__(self, "SourcesView")
        self.window = component.get("MainWindow")
        self.glade = self.window.get_glade()
        self.sources = {}
        self.scolledwindow = self.glade.get_widget("SourcesScrolledWindow")
        self.sourcesvbox = gtk.VBox(False, 0)
        self.scolledwindow.add_with_viewport(self.sourcesvbox)

        self.query_sources_status = LoopingCall(self.query_sources)
        self.sourcesvbox.show()

    def start(self):
        log.debug("Starting %s", self.__class__.__name__)
        client.add_disconnect_callback(self.__on_disconnect)
        client.add_connect_callback(self.__on_connect)
        client.register_event_handler("SourceLoaded", self.on_source_loaded_event)
        client.register_event_handler("SourceBufferingEvent", self.on_source_buffering_event)
        client.register_event_handler("SourcePlaying", self.get_source_status)
        client.register_event_handler("SourcePaused", self.get_source_status)
        client.register_event_handler("SourceStopped", self.get_source_status)
        client.register_event_handler("SourceRemoved", self.on_source_removed_event)
        client.register_event_handler("SourceUpdated", self.on_source_updated_event)
        client.core.get_sources_list().addCallback(self._on_core_get_sources_list)

    def pause(self):
        log.debug("Pausing %s", self.__class__.__name__)
        self.query_sources_status.stop()

    def stop(self):
        log.debug("Stopping %s", self.__class__.__name__)
        client.deregister_event_handler("SourceLoaded", self.on_source_loaded_event)
        client.deregister_event_handler("SourceBufferingEvent", self.on_source_buffering_event)
        client.deregister_event_handler("SourcePlaying", self.get_source_status)
        client.deregister_event_handler("SourcePaused", self.get_source_status)
        client.deregister_event_handler("SourceStopped", self.get_source_status)
        client.deregister_event_handler("SourceRemoved", self.on_source_removed_event)
        client.deregister_event_handler("SourceUpdated", self.on_source_updated_event)
        self.query_sources_status.stop()

    def shutdown(self):
        log.debug("Shutting Down %s", self.__class__.__name__)

    def set_source_status(self, source_id, status):
        self.sources[source_id].set_status(status)

    def on_source_loaded_event(self, source_id):
        client.core.get_source_details(source_id).addCallback(self._on_core_get_source)

    def on_source_buffering_event(self, source_id, buffer_percent):
        if source_id not in self.sources:
            return
        gobject.idle_add(self.sources[source_id].update_progress, buffer_percent)

    # Callbacks
    def _on_core_get_source(self, source):
        log.debug("SOURCE: %s", source)

    def _on_core_get_sources_list(self, sources_list):
        for idx, source in enumerate(sources_list):
            log.trace("_on_core_get_sources_list: %s", source)
            if source["id"] not in self.sources:
                self.sources[source["id"]] = SourceUI(source["id"], source["name"])
                self.sourcesvbox.pack_start(self.sources[source["id"]], False, False, 1)
                self.sources[source["id"]].show_all()
            self.sources[source["id"]].set_status(source['status'])
            self.sources[source["id"]].set_play_status(source["running"])
            self.sources[source["id"]].update_progress(source['buffer_percent'])

    def get_source_status(self, source_id):
        client.core.get_source_details(source_id).addCallback(self.on_get_source_status)

    def on_get_source_status(self, source):
        log.trace("on_get_source_status: %s", source)
        if (source['id'] not in self.sources) and source["enabled"]==True:
            self.sources[source["id"]] = SourceUI(source["id"], source["name"])
            self.sourcesvbox.pack_start(self.sources[source["id"]], False, False, 1)
            self.sources[source["id"]].show_all()
        elif (source['id'] in self.sources) and source["enabled"]==False:
            try:
                source = self.sources.pop(source['id'])
                source.hide()
                source.destroy()
            except KeyError:
                pass
            return
        elif source['id'] not in self.sources:
            return
        self.sources[source["id"]].set_status(source['status'])
        self.sources[source["id"]].set_play_status(source["running"])
        self.sources[source["id"]].update_progress(source['buffer_percent'])

    def on_source_removed_event(self, source_id):
#        if source_id not in self.sources:
#            return
        try:
            source = self.sources.pop(source_id)
            source.hide()
            source.destroy()
            log.debug("Server SourceRemoved. ID: %s", source_id)
        except KeyError:
            pass

    def on_source_updated_event(self, source_id):
        self.get_source_status(source_id)

    def query_sources(self):
        client.core.get_sources_list().addCallback(self._on_core_get_sources_list)

    def __on_disconnect(self):
        client.deregister_event_handler("SourceLoaded", self.on_source_loaded_event)
        client.deregister_event_handler("SourceBufferingEvent", self.on_source_buffering_event)
        client.deregister_event_handler("SourcePlaying", self.get_source_status)
        client.deregister_event_handler("SourcePaused", self.get_source_status)
        client.deregister_event_handler("SourceStopped", self.get_source_status)
        client.deregister_event_handler("SourceRemoved", self.on_source_removed_event)
        try:
            self.query_sources_status.stop()
        except AssertionError:
            # Not running
            pass
        for key in self.sources.copy().keys():
            source = self.sources.pop(key)
            source.hide()
            source.destroy()

    def __on_connect(self):
        client.register_event_handler("SourceLoaded", self.on_source_loaded_event)
        client.register_event_handler("SourceBufferingEvent", self.on_source_buffering_event)
        client.register_event_handler("SourcePlaying", self.get_source_status)
        client.register_event_handler("SourcePaused", self.get_source_status)
        client.register_event_handler("SourceStopped", self.get_source_status)
        client.register_event_handler("SourceRemoved", self.on_source_removed_event)
        client.core.get_sources_list().addCallback(self._on_core_get_sources_list)
        self.query_sources_status.start(5, False)
#
#    def on_query_sources_cb(self, sources):
#        for source in sources:
#            if source["id"] not in self.sources:
#                continue
#            self.sources[source["id"]].set_play_status(source["running"])
