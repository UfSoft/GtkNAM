'''
Created on 5 Sep 2010

@author: vampas
'''

import gtk
import pango
import logging
from gtk import gdk
from nam import common, component

log = logging.getLogger(__name__)

class ToolBar(component.Component):
    def __init__(self):
        component.Component.__init__(self, "ToolBar")
        self.window = component.get("MainWindow")
        self.glade = self.window.get_glade()
        self.toolbar = self.glade.get_widget("ToolBar")
        self.glade.signal_autoconnect(self)

        self.sources_button = self.glade.get_widget("SourcesToolbutton")
        self.accounts_button = self.glade.get_widget("AccountsToolbutton")
        self.connections_button = self.glade.get_widget("ConnectionsToolbutton")

        spacer = self.glade.get_widget('spacer')
        spacer.set_expand(True)

        sources_image = gtk.Image()
        sources_image.set_from_pixbuf(gdk.pixbuf_new_from_file_at_size(
            common.get_pixmap('manage-sources.png'), 32, 32)
        )
        sources_image.show()
        self.sources_button.set_icon_widget(sources_image)

        accounts_image = gtk.Image()
        accounts_image.set_from_pixbuf(gdk.pixbuf_new_from_file_at_size(
            common.get_pixmap('manage-accounts.png'), 32, 32)
        )
        accounts_image.show()
        self.accounts_button.set_icon_widget(accounts_image)

        connections_image = gtk.Image()
        connections_image.set_from_pixbuf(gdk.pixbuf_new_from_file_at_size(
            common.get_pixmap('manage-connections.png'), 32, 32)
        )
        connections_image.show()
        self.connections_button.set_icon_widget(connections_image)

#        combo_tool_item = gtk.ToolItem()
##        combo_tool_item.set_homogeneous(False)
##        combo_tool_item.set_expand(False)
##        combo_tool_item.set_size_request(32, 16)
#        combo = gtk.combo_box_new_text()
#        combo.modify_font(pango.FontDescription("monospace 10"))
#        combo.append_text("Foo")
#        combo.append_text("Bar")
#        combo_tool_item.add(combo)
#        combo_tool_item.show_all()
#        self.toolbar.insert(combo_tool_item, -1)


    def start(self):
        log.debug("Starting %s", self.__class__.__name__)

    def pause(self):
        log.debug("Pausing %s", self.__class__.__name__)

    def stop(self):
        log.debug("Stopping %s", self.__class__.__name__)

    def shutdown(self):
        log.debug("Shutting Down %s", self.__class__.__name__)

    def on_ConnectionsToolbutton_clicked(self, widget):
        component.get("ConnectionManager").show()

    def on_ManageSourcesToolbutton_clicked(self, widget):
        pass

    def on_AccountsToolbutton_clicked(self, widget):
        pass

    def on_MessagesFilterCombobox_changed(self, widget):
        pass


