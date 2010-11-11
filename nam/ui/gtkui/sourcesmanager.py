'''
Created on 5 Sep 2010

@author: vampas
'''

import gtk
import logging
import pkg_resources
from gtk import gdk
from nam import common, component, configmanager
from nam.ui.client import client

log = logging.getLogger(__name__)

(COL_SOURCE_ID, COL_SOURCE_NAME, COL_SOURCE_URI, COL_SOURCE_ENABLED,
 COL_BUFFER_DURATION, COL_BUFFER_SIZE, COL_SILENCE_MIN_TOLERANCE,
 COL_SILENCE_MAX_TOLERANCE, COL_SILENCE_LEVEL, ROW_CHANGED,
 ROW_CHANGED_COLOR) = range(11)


class BaseSourceDialog(object):
    def __init__(self, model=None, treeiter=None, new_item=False):
        self.model = model
        self.treeiter = treeiter
        self.new_item = new_item

        # Get the glade file for the connection manager
        self.glade = gtk.glade.XML(pkg_resources.resource_filename(
            "nam.ui.gtkui", "glade/sources_manager.glade"
        ))
        self.glade.signal_autoconnect(self)

        self.dialog = self.glade.get_widget("EditSourceDialog")

        self.dialog.set_icon(gdk.pixbuf_new_from_file_at_size(
            common.get_pixmap('manage-sources.png'), 16, 16
        ))

        self.input_name = self.glade.get_widget("SourceName")
        self.input_uri = self.glade.get_widget("SourceUri")
        self.input_buffer_size = self.glade.get_widget("SourceBufferSize")
        self.input_buffer_duration = self.glade.get_widget("SourceBufferDuration")
        self.input_enabled = self.glade.get_widget("SourceEnabled")
        self.input_min_tolerance = self.glade.get_widget("SilenceMinTolerance")
        self.input_max_tolerance = self.glade.get_widget("SilenceMaxTolerance")
        self.input_total_tolerance = self.glade.get_widget("SilenceTotalTolerance")
        self.input_level = self.glade.get_widget("SilenceLevel")

        self.button_add = self.glade.get_widget("SourceAddButton")
        self.button_apply = self.glade.get_widget("SourceApplyButton")
        self.button_cancel = self.glade.get_widget("SourceCancelButton")


    def show(self):
        self.dialog.show_all()
        if self.new_item:
            self.dialog.set_title("Add New Audio Source")
            self.button_add.show()
            self.button_apply.hide()
            return

        self.button_add.hide()
        self.button_apply.show()
        self.dialog.set_title("Edit Audio Source")

        self.input_name.set_text(self.model[self.treeiter][COL_SOURCE_NAME])
        self.input_uri.set_text(self.model[self.treeiter][COL_SOURCE_URI])
        self.input_buffer_size.set_value(self.model[self.treeiter][COL_BUFFER_SIZE])
        self.input_buffer_duration.set_value(self.model[self.treeiter][COL_BUFFER_DURATION])
        self.input_enabled.set_active(self.model[self.treeiter][COL_SOURCE_ENABLED])
        self.input_min_tolerance.set_value(self.model[self.treeiter][COL_SILENCE_MIN_TOLERANCE])
        self.input_max_tolerance.set_value(self.model[self.treeiter][COL_SILENCE_MAX_TOLERANCE])
        self.input_level.set_value(self.model[self.treeiter][COL_SILENCE_LEVEL])

        self.on_silence_tolerance_changed(None)
        self.input_total_tolerance.set_editable(False)
        self.input_total_tolerance.set_property("can-focus", False)

    def run(self):
        self.show()
        return self.dialog.run()

    def destroy(self):
        return self.dialog.destroy()

    def on_SourceCancelButton_clicked(self, widget):
        self.dialog.hide()

    def on_SourceApplyButton_clicked(self, widget):
        self.dialog.hide()

    def on_SourceAddButton_clicked(self, widget):
        self.dialog.hide()

    def on_input_changed(self, *args):
        self.button_apply.set_sensitive(True)
        self.button_add.set_sensitive(True)

    def on_silence_tolerance_changed(self, widget):
        min = self.input_min_tolerance.get_value()
        max = self.input_max_tolerance.get_value()
        total = min + max
        log.debug("Updating Total silence tolerance to %s", total)
        self.input_total_tolerance.set_text(str(total))

    on_SourceName_changed = on_input_changed
    on_SourceUri_changed = on_input_changed
    on_SourceBufferSize_changed = on_input_changed
    on_SourceBufferDuration_changed = on_input_changed
    on_SourceEnabled_toggled = on_input_changed
    on_SilenceLevel_changed = on_input_changed
    on_SilenceMinTolerance_changed = on_silence_tolerance_changed
    on_SilenceMaxTolerance_changed = on_silence_tolerance_changed

class EditSource(BaseSourceDialog):
    def __init__(self, model, treeiter):
        BaseSourceDialog.__init__(self, model, treeiter, new_item=False)


class AddSource(BaseSourceDialog):
    def __init__(self):
        BaseSourceDialog.__init__(self, model=None, treeiter=None, new_item=True)


class SourcesManager(component.Component):
    def __init__(self):
        component.Component.__init__(self, "SourcesManagerGtk")
        self.running = False

    # Component overrides
    def start(self):
        self.config = configmanager.ConfigManager("gtkui.conf")

    def stop(self):
        # Close this dialog when we are shutting down
        if self.running:
            self.sources_manager.response(gtk.RESPONSE_CLOSE)

    def shutdown(self):
        pass

    # Public methods
    def show(self):
        """
        Show the ConnectionManager dialog.
        """
        self.loaded_sources = {}
        # Get the glade file for the connection manager
        self.glade = gtk.glade.XML(pkg_resources.resource_filename(
            "nam.ui.gtkui", "glade/sources_manager.glade"
        ))
        self.glade.signal_autoconnect(self)

        self.window = component.get("MainWindow")

        self.treeview = self.glade.get_widget("ManageSourcesTreeview")
        self.button_add = self.glade.get_widget("AddSourceButton")
        self.button_edit = self.glade.get_widget("EditSourceButton")
        self.button_delete = self.glade.get_widget("DeleteSourceButton")

        # Setup the Sources Manager dialog
        self.sources_manager = self.glade.get_widget("ManageSourcesDialog")
        self.sources_manager.set_transient_for(self.window.window)

        self.sources_manager.set_icon(gdk.pixbuf_new_from_file_at_size(
            common.get_pixmap('manage-sources.png'), 16, 16
        ))

        self.liststore = gtk.ListStore(
            int,    # COL_SOURCE_ID
            str,    # COL_SOURCE_NAME
            str,    # COL_SOURCE_URI
            bool,   # COL_SOURCE_ENABLED
            int,    # COL_BUFFER_DURATION
            float,  # COL_BUFFER_SIZE
            int,    # COL_SILENCE_MIN_TOLERANCE
            int,    # COL_SILENCE_MAX_TOLERANCE
            float,  # COL_SILENCE_LEVEL
            bool,   # ROW_CHANGED
            str,    # ROW_CHANGED_COLOR
        )
        self.treeview.set_model(self.liststore)

        client.core.get_sources_list(disabled=True).addCallback(
            self.on_core_get_sources_list
        )

        # COL_SOURCE_ID
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("ID", renderer, text=COL_SOURCE_ID)
        column.set_visible(False)
        self.treeview.append_column(column)

        # COL_SOURCE_NAME
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Name", renderer, text=COL_SOURCE_NAME)
        column.set_sort_column_id(COL_SOURCE_NAME)
        column.add_attribute(renderer, 'background-set', ROW_CHANGED)
        column.add_attribute(renderer, 'background', ROW_CHANGED_COLOR)
        self.treeview.append_column(column)

        # COL_SOURCE_URI
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("URI", renderer, text=COL_SOURCE_URI)
        column.set_sort_column_id(COL_SOURCE_URI)
        column.add_attribute(renderer, 'background-set', ROW_CHANGED)
        column.add_attribute(renderer, 'background', ROW_CHANGED_COLOR)
        self.treeview.append_column(column)

        # COL_SOURCE_ENABLED
        renderer = gtk.CellRendererToggle()
        renderer.set_radio(False)
        renderer.set_activatable(True)

        column = gtk.TreeViewColumn("Enabled", renderer)
        column.add_attribute(renderer, "active", COL_SOURCE_ENABLED)
        column.set_sort_column_id(COL_SOURCE_ENABLED)
#        column.add_attribute(renderer, 'background-set', ROW_CHANGED)
#        column.add_attribute(renderer, 'background', ROW_CHANGED_COLOR)
        self.treeview.append_column(column)

        # COL_BUFFER_DURATION
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Buffer Duration", renderer, text=COL_BUFFER_DURATION)
        column.set_visible(False)
        self.treeview.append_column(column)

        # COL_BUFFER_SIZE
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Buffer Size", renderer, text=COL_BUFFER_SIZE)
        column.set_visible(False)
        self.treeview.append_column(column)

        # COL_SILENCE_MIN_TOLERANCE
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Silence Minimum Tolerance", renderer,
                                    text=COL_SILENCE_MIN_TOLERANCE)
        column.set_visible(False)
        self.treeview.append_column(column)

        # COL_SILENCE_MAX_TOLERANCE
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Silence Maximum Tolerance", renderer,
                                    text=COL_SILENCE_MAX_TOLERANCE)
        column.set_visible(False)
        self.treeview.append_column(column)

        # COL_SILENCE_LEVEL
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Silence Level", renderer, text=COL_SILENCE_LEVEL)
        column.set_visible(False)
        self.treeview.append_column(column)

        # ROW_CHANGED
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Changed", renderer, text=ROW_CHANGED)
        column.set_visible(False)
        self.treeview.append_column(column)

        self.treeview.get_selection().connect(
            "changed", self.on_source_selection_changed
        )

        client.register_event_handler("SourceAdded", self.on_core_source_added)
        client.register_event_handler("SourceRemoved", self.on_core_source_removed)
        client.register_event_handler("SourceUpdated", self.on_core_source_updated)

        # Load the window state
        self.load_dialog_state()
        self.sources_manager.connect("window-state-event", self.on_window_state_event)
        self.sources_manager.connect("configure-event", self.on_window_configure_event)
        self.sources_manager.connect("delete-event", self.on_window_delete_event)
        self.sources_manager.connect("expose-event", self.on_expose_event)

        self.sources_manager.show_all()

    def load_dialog_state(self):
        x = self.config["sourcesmanager"]["window_x_pos"]
        y = self.config["sourcesmanager"]["window_y_pos"]
        w = self.config["sourcesmanager"]["window_width"]
        h = self.config["sourcesmanager"]["window_height"]
        self.sources_manager.move(x, y)
        self.sources_manager.resize(w, h)
        if self.config["sourcesmanager"]["window_maximized"]:
            self.sources_manager.maximize()

    def on_window_configure_event(self, widget, event):
        if not self.config["sourcesmanager"]["window_maximized"]:
            (self.config["sourcesmanager"]["window_x_pos"],
             self.config["sourcesmanager"]["window_y_pos"]) = self.sources_manager.get_position()
            self.config["sourcesmanager"]["window_width"] = event.width
            self.config["sourcesmanager"]["window_height"] = event.height

    def on_window_state_event(self, widget, event):
        if event.changed_mask & gdk.WINDOW_STATE_MAXIMIZED:
            if event.new_window_state & gdk.WINDOW_STATE_MAXIMIZED:
                log.debug("pos: %s", self.sources_manager.get_position())
                self.config["sourcesmanager"]["window_maximized"] = True
            else:
                self.config["sourcesmanager"]["window_maximized"] = False
        return False

    def on_window_delete_event(self, widget, event):
        self.config.save()
        return True

    def on_expose_event(self, widget, event):
        # XXX:
        pass


    def on_core_get_sources_list(self, sources_list):
        log.debug("Got Sources List From Core")
        self.liststore.clear()
        for source in sources_list:
            self.loaded_sources[source["id"]] = source
            self.liststore.append((
                source["id"],                       # COL_SOURCE_ID
                source["name"],                     # COL_SOURCE_NAME
                source["uri"],                      # COL_SOURCE_URI
                source["enabled"],                  # COL_SOURCE_ENABLED
                source["buffer_duration"],          # COL_BUFFER_DURATION
                source["buffer_size"],              # COL_BUFFER_SIZE
                source["silence"]["min_tolerance"], # COL_SILENCE_MIN_TOLERANCE
                source["silence"]["max_tolerance"], # COL_SILENCE_MAX_TOLERANCE
                source["silence"]["silence_level"], # COL_SILENCE_LEVEL
                False,                              # ROW_CHANGED
                "lightyellow"                       # ROW_CHANGED_COLOR
            ))

    def on_core_source_added(self, source_id):
        log.debug("Source Added on Core")
        client.core.get_source_details(source_id).addCallback(self.on_core_got_source_details)

    def on_core_source_updated(self, source_id):
        log.debug("Source Updated on Core")
        client.core.get_source_details(source_id).addCallback(self.on_core_got_source_details)

    def on_core_source_removed(self, source_id):
        log.debug("Source Removed on Core")
        if source_id not in self.loaded_sources:
            return
        del self.loaded_sources[source_id]
        def remove_item(model, path, iter):
            if model[iter][COL_SOURCE_ID] == source_id:
                self.liststore.remove(iter)
        self.liststore.foreach(remove_item)

    def on_core_got_source_details(self, source_details):
        if source_details['id'] not in self.loaded_sources:
            log.debug("Adding source to liststore")
            self.loaded_sources[source_details['id']] = source_details
            self.liststore.append((
                source_details["id"],                       # COL_SOURCE_ID
                source_details["name"],                     # COL_SOURCE_NAME
                source_details["uri"],                      # COL_SOURCE_URI
                source_details["enabled"],                  # COL_SOURCE_ENABLED
                source_details["buffer_duration"],          # COL_BUFFER_DURATION
                source_details["buffer_size"],              # COL_BUFFER_SIZE
                source_details["silence"]["min_tolerance"], # COL_SILENCE_MIN_TOLERANCE
                source_details["silence"]["max_tolerance"], # COL_SILENCE_MAX_TOLERANCE
                source_details["silence"]["silence_level"], # COL_SILENCE_LEVEL
                False,                                      # ROW_CHANGED
                "lightyellow"                               # ROW_CHANGED_COLOR
            ))
            return

        def update_details(model, path, iter):
            if model[iter][COL_SOURCE_ID] != source_details['id']:
                return
            log.debug("Updating source in liststore")
            model[iter][COL_SOURCE_NAME] = source_details["name"]
            model[iter][COL_SOURCE_URI] = source_details["uri"]
            model[iter][COL_SOURCE_ENABLED] = source_details["enabled"]
            model[iter][COL_BUFFER_DURATION] = source_details["buffer_duration"]
            model[iter][COL_BUFFER_SIZE] = source_details["buffer_size"]
            model[iter][COL_SILENCE_MIN_TOLERANCE] = source_details["silence"]["min_tolerance"]
            model[iter][COL_SILENCE_MAX_TOLERANCE] = source_details["silence"]["max_tolerance"]
            model[iter][COL_SILENCE_LEVEL] = source_details["silence"]["silence_level"]
            model[iter][ROW_CHANGED] = False
            model[iter][ROW_CHANGED_COLOR] = "lightyellow"
        self.liststore.foreach(update_details)

    def on_source_selection_changed(self, treeselection):
        model, treeiter = treeselection.get_selected()
        self.button_delete.set_sensitive(treeiter is not None)
        self.button_edit.set_sensitive(treeiter is not None)

#    def on_row_item_changed(self, *args):
#        log.debug("Row Changed: %s", args)
#        model, treeiter = self.treeview.get_selection().get_selected()
#        self.button_source_apply.set_sensitive(treeiter is not None)
#        if not treeiter:
#            return
#        log.debug("Model: %s  Treeiter: %s", model, treeiter)
#        model[treeiter][ROW_CHANGED] = True
#
#    on_SourceName_changed = on_row_item_changed
#    on_SourceUri_changed = on_row_item_changed
#    on_SourceBufferSize_changed = on_row_item_changed
#    on_SourceBufferDuration_changed = on_row_item_changed
#    on_SourceEnabled_toggled = on_row_item_changed
#    on_SilenceMinTolerance_changed = on_row_item_changed
#    on_SilenceMaxTolerance_changed = on_row_item_changed
#    on_SilenceLevel_changed = on_row_item_changed

    def on_ManageSourcesCloseButton_clicked(self, button):
        self.loaded_sources = {}
        self.liststore.clear()
        client.deregister_event_handler("SourceAdded", self.on_core_source_added)
        client.deregister_event_handler("SourceRemoved", self.on_core_source_removed)
        client.deregister_event_handler("SourceUpdated", self.on_core_source_updated)

        self.window_x_pos, self.window_y_pos = self.sources_manager.get_position()

        self.sources_manager.destroy()

    def on_ManageSourcesTreeview_cursor_changed(self, treeview):
        pass

    def on_AddSourceButton_clicked(self, button):
        dialog = AddSource()
        dialog.dialog.set_transient_for(self.sources_manager)
        if dialog.run() == 1:
            name = dialog.input_name.get_text()
            uri = dialog.input_uri.get_text()
            buffer_size = dialog.input_buffer_size.get_value()
            buffer_duration = dialog.input_buffer_duration.get_value()
            active = dialog.input_enabled.get_active()
            min_tolerance = dialog.input_min_tolerance.get_value()
            max_tolerance = dialog.input_max_tolerance.get_value()
            level = dialog.input_level.get_value()
            client.core.add_source(name, uri, buffer_size, buffer_duration,
                                   active, min_tolerance, max_tolerance, level)

        dialog.destroy()

    def on_EditSourceButton_clicked(self, button):
        model, treeiter = self.treeview.get_selection().get_selected()
        if not treeiter:
            self.button_edit.set_sensitive(False)
            return
        dialog = EditSource(model, treeiter)
        dialog.dialog.set_transient_for(self.sources_manager)
        if dialog.run() == 1:
            source_id = model[treeiter][COL_SOURCE_ID]
            name= dialog.input_name.get_text()
            uri= dialog.input_uri.get_text()
            buffer_size= dialog.input_buffer_size.get_value()
            buffer_duration= dialog.input_buffer_duration.get_value()
            active= dialog.input_enabled.get_active()
            min_tolerance= dialog.input_min_tolerance.get_value()
            max_tolerance= dialog.input_max_tolerance.get_value()
            level= dialog.input_level.get_value()
            client.core.alter_source(source_id, name, uri, buffer_size,
                                     buffer_duration, active, min_tolerance,
                                     max_tolerance, level)
        dialog.destroy()

    def on_DeleteSourceButton_clicked(self, button):
        model, treeiter = self.treeview.get_selection().get_selected()
        if not treeiter:
            self.button_delete.set_sensitive(False)
            return
        source_id = model[treeiter][COL_SOURCE_ID]
        log.debug("User is trying to remove source id: %s", source_id)
        client.core.remove_source(source_id)
