#
# statusbar.py
#
# Copyright (C) 2007, 2008 Andrew Resch <andrewresch@gmail.com>
# Copyright (C) 2010 Pedro Algarvio <pedro@algarvio.me>
#
# Deluge is free software.
#
# You may redistribute it and/or modify it under the terms of the
# GNU General Public License, as published by the Free Software
# Foundation; either version 3 of the License, or (at your option)
# any later version.
#
# deluge is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with deluge.    If not, write to:
# 	The Free Software Foundation, Inc.,
# 	51 Franklin Street, Fifth Floor
# 	Boston, MA  02110-1301, USA.
#
#    In addition, as a special exception, the copyright holders give
#    permission to link the code of portions of this program with the OpenSSL
#    library.
#    You must obey the GNU General Public License in all respects for all of
#    the code used other than OpenSSL. If you modify file(s) with this
#    exception, you may extend this exception to your version of the file(s),
#    but you are not obligated to do so. If you do not wish to do so, delete
#    this exception statement from your version. If you delete this exception
#    statement from all source files in the program, then also delete it here.
#
#


import gtk
import gobject
import logging

from nam.ui.client import client
import nam.component as component
import nam.common
from nam.ui.gtkui import common
from nam.configmanager import ConfigManager

log = logging.getLogger(__name__)

class StatusBarItem:
    def __init__(self, image=None, stock=None, text=None, callback=None, tooltip=None):
        self._widgets = []
        self._ebox = gtk.EventBox()
        self._hbox = gtk.HBox()
        self._hbox.set_spacing(5)
        self._image = gtk.Image()
        self._label = gtk.Label()
        self._hbox.add(self._image)
        self._hbox.add(self._label)
        self._ebox.add(self._hbox)

        # Add image from file or stock
        if image != None or stock != None:
            if image != None:
                self.set_image_from_file(image)
            if stock != None:
                self.set_image_from_stock(stock)

        # Add text
        if text != None:
            self.set_text(text)

        if callback != None:
            self.set_callback(callback)

        if tooltip:
            self.set_tooltip(tooltip)

        self.show_all()

    def set_callback(self, callback):
        self._ebox.connect("button-press-event", callback)

    def show_all(self):
        self._ebox.show()
        self._hbox.show()
        self._image.show()
        self._label.show()

    def hide(self):
        self._ebox.hide()
        self._hbox.hide()
        self._image.hide()
        self._label.hide()

    def set_image_from_file(self, image):
        self._image.set_from_file(image)

    def set_image_from_stock(self, stock):
        self._image.set_from_stock(stock, gtk.ICON_SIZE_MENU)

    def set_text(self, text):
        if self._label.get_text() != text:
            self._label.set_text(text)

    def set_tooltip(self, tip):
        if self._ebox.get_tooltip_text() != tip:
            self._ebox.set_tooltip_text(tip)

    def get_widgets(self):
        return self._widgets

    def get_eventbox(self):
        return self._ebox

    def get_text(self):
        return self._label.get_text()

class StatusBar(component.Component):
    def __init__(self):
        component.Component.__init__(self, "StatusBar", interval=3)
        self.window = component.get("MainWindow")
        self.statusbar = self.window.glade.get_widget("StatusBar")
        self.config = ConfigManager("gtkui.conf")

        self.current_warnings = []
        # Add a HBox to the statusbar after removing the initial label widget
        self.hbox = gtk.HBox()
        self.hbox.set_spacing(10)
        frame = self.statusbar.get_children()[0]
        frame.remove(frame.get_children()[0])
        frame.add(self.hbox)
        self.statusbar.show_all()
        # Create the connected item
        self.connected_item = StatusBarItem(
            stock=gtk.STOCK_CONNECT, text=_("Connected")
        )
        self.hbox.pack_start(
            self.connected_item.get_eventbox(), expand=False, fill=False
        )
        # Create the not connected item
        self.not_connected_item = StatusBarItem(
            stock=gtk.STOCK_DISCONNECT, text=_("Not Connected"),
            callback=self._on_notconnected_item_clicked)
        self.hbox.pack_start(
            self.not_connected_item.get_eventbox(), expand=False, fill=False
        )
        # Show the not connected status bar
        self.show_not_connected()


        self.traffic_item = self.add_item(
            image=nam.common.get_pixmap("traffic16.png"),
#            callback=self._on_traffic_item_clicked,
            tooltip=_("Protocol Traffic Download/Upload"))
        self.traffic_item.hide()

        # Hide if necessary
        self.visible(self.config["show_statusbar"])

        client.register_event_handler("ConfigValueChangedEvent", self.on_configvaluechanged_event)
        client.add_disconnect_callback(self.__on_disconnect)
        client.add_connect_callback(self.__on_connect)

    def start(self):
        if client.connected():
            self.show_connected()
        # Add in images and labels
#        self.remove_item(self.not_connected_item)

#        self.connections_item = self.add_item(
#            stock=gtk.STOCK_NETWORK,
#            callback=self._on_connection_item_clicked,
#            tooltip=_("Connections"))

#        self.download_item = self.add_item(
#            image=deluge.common.get_pixmap("downloading16.png"),
#            callback=self._on_download_item_clicked,
#            tooltip=_("Download Speed"))
#
#        self.upload_item = self.add_item(
#            image=deluge.common.get_pixmap("seeding16.png"),
#            callback=self._on_upload_item_clicked,
#            tooltip=_("Upload Speed"))
#

    def stop(self):
        self.show_not_connected()

    def visible(self, visible):
        if visible:
            self.statusbar.show()
        else:
            self.statusbar.hide()

        self.config["show_statusbar"] = visible

    def show_not_connected(self):
        self.connected_item.get_eventbox().hide()
        self.not_connected_item.get_eventbox().show()

    def show_connected(self):
        self.not_connected_item.get_eventbox().hide()
        self.connected_item.get_eventbox().show()

    def add_item(self, image=None, stock=None, text=None, callback=None, tooltip=None):
        """Adds an item to the status bar"""
        # The return tuple.. we return whatever widgets we add
        item = StatusBarItem(image, stock, text, callback, tooltip)
        self.hbox.pack_start(item.get_eventbox(), expand=False, fill=False)
        return item

    def remove_item(self, item):
        """Removes an item from the statusbar"""
        if item.get_eventbox() in self.hbox.get_children():
            try:
                self.hbox.remove(item.get_eventbox())
            except Exception, e:
                log.debug("Unable to remove widget: %s", e)

    def add_timeout_item(self, seconds=3, image=None, stock=None, text=None, callback=None):
        """Adds an item to the StatusBar for seconds"""
        item = self.add_item(image, stock, text, callback)
        # Start a timer to remove this item in seconds
        gobject.timeout_add(seconds * 1000, self.remove_item, item)

    def display_warning(self, text, callback=None):
        """Displays a warning to the user in the status bar"""
        if text not in self.current_warnings:
            item = self.add_item(
                stock=gtk.STOCK_DIALOG_WARNING, text=text, callback=callback)
            self.current_warnings.append(text)
            gobject.timeout_add(3000, self.remove_warning, item)

    def remove_warning(self, item):
        self.current_warnings.remove(item.get_text())
        self.remove_item(item)

    def clear_statusbar(self):
        def remove(child):
            self.hbox.remove(child)
        self.hbox.foreach(remove)


    def on_configvaluechanged_event(self, key, value):
        """
        This is called when we receive a ConfigValueChangedEvent from
        the core.
        """

        if key in self.config_value_changed_dict.keys():
            self.config_value_changed_dict[key](value)

    def __on_disconnect(self):
        self.show_not_connected()
        self.traffic_item.hide()

    def __on_connect(self):
        self.show_connected()
        self.traffic_item.show_all()
        connection_info = client.connection_info()
        if connection_info:
            tooltip = "User \"%s\" connected to %s:%s" % (connection_info[2],
                                                          connection_info[0],
                                                          connection_info[1])
            self.connected_item.set_tooltip(tooltip)

    def _on_notconnected_item_clicked(self, widget, event):
        component.get("ConnectionManager").show()
