'''
Created on 4 Sep 2010

@author: vampas
'''

import gtk
import logging
from nam import component
from nam.ui.client import client

log = logging.getLogger(__name__)


(COL_MESSAGE_KIND, COL_MESSAGE_KIND_TXT, COL_MESSAGE_DATE, COL_MESSAGE_TIME,
 COL_MESSAGE_SOURCE_ID, COL_MESSAGE_SOURCE_NAME, COL_MESSAGE_TEXT,
 COL_MESSAGE_ROW_COLOR) = range(8)

class MessagesView(component.Component):
    def __init__(self):
        component.Component.__init__(self, "MessagesView")
        self.window = component.get("MainWindow")
        self.treeview = self.window.glade.get_widget("MessagesTreeview")
        self.sources = {}

        self.store = self.create_model()
        self.create_columns()

        self.treeview.set_model(self.store)
        self.treeview.show_all()

    def start(self):
        log.debug("Starting %s", self.__class__.__name__)
        client.core.get_message_kinds().addCallback(self._on_core_get_message_kinds)
        client.core.get_sources_list().addCallback(self._on_core_get_sources_list)
        client.register_event_handler("SourceLoaded", self.on_source_loaded_event)
        client.register_event_handler("AudioSilenceEvent", self._on_audio_silence_event)

    def pause(self):
        log.debug("Pausing %s", self.__class__.__name__)

    def stop(self):
        log.debug("Stopping %s", self.__class__.__name__)
        client.deregister_event_handler("SourceLoaded", self.on_source_loaded_event)
        client.deregister_event_handler("AudioSilenceEvent", self._on_audio_silence_event)

    def shutdown(self):
        log.debug("Shutting Down %s", self.__class__.__name__)

    def on_source_loaded_event(self, source_id):
        client.core.get_source(source_id).addCallback(self._on_core_get_source)

    def _on_core_get_source(self, source):
        log.debug("SOURCE: %s", source)
        self.sources[source.src_id] = source.src_name

    def _on_core_get_sources_list(self, sources_list):
        for source in sources_list:
            self.sources[source["id"]] = source["name"]

    def _on_core_get_message_kinds(self, kinds):
        self.messages_kinds = {}
        self.messages_kinds_colors = {}
        for kind in kinds:
            self.messages_kinds[kind['id']] = kind['kind']
            if kind['kind'] == 'OK':
                self.messages_kinds_colors[kind['id']] = 'blue'
            elif kind['kind'] == 'WARNING':
                self.messages_kinds_colors[kind['id']] = 'orange'
            elif kind['kind'] == 'ERROR':
                self.messages_kinds_colors[kind['id']] = 'red'

    def _on_audio_silence_event(self, stamp, source_id, kind, message, levels):
#    def _on_audio_silence_event(self, *event):
#        import pprint
#        pprint.pprint(event)
#        return
        row_iter = self.store.append()
        date, time = stamp.split("|")
        self.store.set(row_iter,
            COL_MESSAGE_KIND,           kind,
            COL_MESSAGE_KIND_TXT,       self.messages_kinds[kind],
            COL_MESSAGE_DATE,           date,
            COL_MESSAGE_TIME,           time,
            COL_MESSAGE_SOURCE_ID,      source_id,
            COL_MESSAGE_SOURCE_NAME,    self.sources[source_id],
            COL_MESSAGE_TEXT,           message,
            COL_MESSAGE_ROW_COLOR,      self.messages_kinds_colors[kind],
        )
        self.treeview.scroll_to_cell(self.store.get_path(row_iter))
        component.get("SourcesView").get_source_status(source_id)

    def create_model(self):
        return gtk.ListStore(
            int,    # Message Kind
            str,    # Message Kind Name
            str,    # Message Date
            str,    # Message Time
            int,    # Source ID
            str,    # Source Name
            str,    # Message Text
            str,    # row color
        )

    def create_columns(self):
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("KIND ID", renderer, text=COL_MESSAGE_KIND)
        column.set_sort_column_id(COL_MESSAGE_KIND)
        column.set_visible(False)
        self.treeview.append_column(column)

        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Type", renderer, text=COL_MESSAGE_KIND_TXT)
        column.set_sort_column_id(COL_MESSAGE_KIND_TXT)
        column.add_attribute(renderer, 'foreground', COL_MESSAGE_ROW_COLOR)
        column.add_attribute(renderer, 'foreground-set', True)
        self.treeview.append_column(column)

        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Date", renderer, text=COL_MESSAGE_DATE)
        column.set_sort_column_id(COL_MESSAGE_DATE)
        column.set_visible(False)
        self.treeview.append_column(column)

        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Time", renderer, text=COL_MESSAGE_TIME)
        column.set_sort_column_id(COL_MESSAGE_TIME)
        column.add_attribute(renderer, 'foreground', COL_MESSAGE_ROW_COLOR)
        column.add_attribute(renderer, 'foreground-set', True)
        self.treeview.append_column(column)

        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Source ID", renderer, text=COL_MESSAGE_SOURCE_ID)
        column.set_sort_column_id(COL_MESSAGE_SOURCE_ID)
        column.set_visible(False)
        self.treeview.append_column(column)

        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Source Name", renderer, text=COL_MESSAGE_SOURCE_NAME)
        column.set_sort_column_id(COL_MESSAGE_SOURCE_NAME)
        column.add_attribute(renderer, 'foreground', COL_MESSAGE_ROW_COLOR)
        column.add_attribute(renderer, 'foreground-set', True)
        self.treeview.append_column(column)

        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Message", renderer, text=COL_MESSAGE_TEXT)
        column.set_sort_column_id(COL_MESSAGE_TEXT)
        column.add_attribute(renderer, 'foreground', COL_MESSAGE_ROW_COLOR)
        column.add_attribute(renderer, 'foreground-set', True)
        self.treeview.append_column(column)

        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("ROW COLOR", renderer, text=COL_MESSAGE_ROW_COLOR)
        column.set_sort_column_id(COL_MESSAGE_ROW_COLOR)
        column.set_visible(False)
        self.treeview.append_column(column)
