#
# mainwindow.py
#
# Copyright (C) 2007 Andrew Resch <andrewresch@gmail.com>
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


import pygtk
pygtk.require('2.0')
import gtk, gtk.glade
import gobject
import pkg_resources
from urlparse import urlparse
import urllib
import logging

from nam.ui.client import client
import nam.component as component
from nam.configmanager import ConfigManager
#from nam.ui.gtkui.ipcinterface import process_args
from twisted.internet import reactor

import nam.common
from nam.ui.gtkui import common

log = logging.getLogger(__name__)

class MainWindow(component.Component):
    def __init__(self):
        component.Component.__init__(self, "MainWindow", interval=2)
        self.config = ConfigManager("gtkui.conf")
        # Get the glade file for the main window
        self.glade = gtk.glade.XML(pkg_resources.resource_filename(
            "nam.ui.gtkui", "glade/main_window.glade"
        ))

        self.window = self.glade.get_widget("GtkNAMMainWindow")

        self.window.set_icon(common.get_nam_icon())

        self.hpaned = self.glade.get_widget("MainContentHPaned")
        self.initial_hpaned_position = self.config["window_hpane_position"]

        # Load the window state
        self.load_window_state()

        # Keep track of window's minimization state so that we don't update the
        # UI when it is minimized.
        self.is_minimized = False

        # Connect events
        self.window.connect("window-state-event", self.on_window_state_event)
        self.window.connect("configure-event", self.on_window_configure_event)
        self.window.connect("delete-event", self.on_window_delete_event)
        self.window.connect("expose-event", self.on_expose_event)
        self.hpaned.connect("notify::position", self.on_hpaned_position_event)

#        self.config.register_set_function(
#            "show_rate_in_title",
#            self._on_set_show_rate_in_title,
#            apply_now=False
#        )

        client.register_event_handler(
            "NewVersionAvailableEvent",
            self.on_newversionavailable_event
        )
#        client.register_event_handler("TorrentFinishedEvent", self.on_torrentfinished_event)

    def first_show(self):
        if not(self.config["start_in_tray"] and \
               self.config["enable_system_tray"]) and not \
                self.window.get_property("visible"):
            log.debug("Showing window")
            self.show()
            while gtk.events_pending():
                gtk.main_iteration(False)
            self.hpaned.set_position(self.initial_hpaned_position)

    def show(self):
#        try:
#            component.resume("TorrentView")
#            component.resume("StatusBar")
#            component.resume("TorrentDetails")
#        except:
#            pass

        self.window.show()


    def hide(self):
#        component.pause("TorrentView")
#        component.get("TorrentView").save_state()
#        component.pause("StatusBar")
#        component.pause("TorrentDetails")
        # Store the x, y positions for when we restore the window
        self.window_x_pos = self.window.get_position()[0]
        self.window_y_pos = self.window.get_position()[1]
        self.window.hide()

    def present(self):
        # Restore the proper x,y coords for the window prior to showing it
        try:
            self.config["window_x_pos"] = self.window_x_pos
            self.config["window_y_pos"] = self.window_y_pos
        except:
            pass
#        try:
#            component.resume("TorrentView")
#            component.resume("StatusBar")
#            component.resume("TorrentDetails")
#        except:
#            pass

        self.window.present()
        self.load_window_state()

    def active(self):
        """Returns True if the window is active, False if not."""
        return self.window.is_active()

    def visible(self):
        """Returns True if window is visible, False if not."""
        return self.window.get_property("visible")

    def get_glade(self):
        """Returns a reference to the main window glade object."""
        return self.glade

    def quit(self):
        self.config.save()
        reactor.stop()

    def load_window_state(self):
        x = self.config["window_x_pos"]
        y = self.config["window_y_pos"]
        w = self.config["window_width"]
        h = self.config["window_height"]
        self.window.move(x, y)
        self.window.resize(w, h)
        if self.config["window_maximized"]:
            self.window.maximize()

    def on_window_configure_event(self, widget, event):
        if not self.config["window_maximized"] and self.visible:
            self.config["window_x_pos"] = self.window.get_position()[0]
            self.config["window_y_pos"] = self.window.get_position()[1]
            self.config["window_width"] = event.width
            self.config["window_height"] = event.height

    def on_window_state_event(self, widget, event):
        if event.changed_mask & gtk.gdk.WINDOW_STATE_MAXIMIZED:
            if event.new_window_state & gtk.gdk.WINDOW_STATE_MAXIMIZED:
                log.debug("pos: %s", self.window.get_position())
                self.config["window_maximized"] = True
            else:
                self.config["window_maximized"] = False
        if event.changed_mask & gtk.gdk.WINDOW_STATE_ICONIFIED:
            if event.new_window_state & gtk.gdk.WINDOW_STATE_ICONIFIED:
                log.debug("MainWindow is minimized..")
#                component.pause("TorrentView")
                component.pause("StatusBar")
                self.is_minimized = True
            else:
                log.debug("MainWindow is not minimized..")
                try:
#                    component.resume("TorrentView")
                    component.resume("StatusBar")
                except:
                    pass
                self.is_minimized = False
        return False

    def on_window_delete_event(self, widget, event):
        if self.config["close_to_tray"] and self.config["enable_system_tray"]:
            self.hide()
        else:
            self.quit()

        return True

    def on_hpaned_position_event(self, obj, param):
        self.config["window_hpane_position"] = self.hpaned.get_position()

#    def on_drag_data_received_event(self, widget, drag_context, x, y, selection_data, info, timestamp):
#        args = []
#        for uri in selection_data.data.split():
#            if nam.common.windows_check():
#                args.append(urllib.url2pathname(uri[7:]))
#            else:
#                args.append(urllib.unquote(urlparse(uri).path))
#        process_args(args)
#        drag_context.finish(True, True)

    def on_expose_event(self, widget, event):
        # XXX:
        pass
#        component.get("SystemTray").blink(False)

    def stop(self):
        self.window.set_title("Network Audio Monitor")

    def update(self):
        # Update the window title
        def _on_get_session_status(status):
            download_rate = nam.common.fspeed(status["download_rate"])
            upload_rate = nam.common.fspeed(status["upload_rate"])
            self.window.set_title("Network Audio Monitor - %s %s %s %s" % (
                _("Down:"), download_rate, _("Up:"), upload_rate)
            )
#        if self.config["show_rate_in_title"]:
#            client.core.get_session_status([
#                "download_rate", "upload_rate"
#            ]).addCallback(_on_get_session_status)

    def _on_set_show_rate_in_title(self, key, value):
        if value:
            self.update()
        else:
            self.window.set_title("Network Audio Monitor")

    def on_newversionavailable_event(self, new_version):
        if self.config["show_new_releases"]:
            from nam.ui.gtkui.new_release_dialog import NewReleaseDialog
            reactor.callLater(5.0, NewReleaseDialog().show, new_version)

#    def on_torrentfinished_event(self, torrent_id):
#        from nam.ui.gtkui.notification import Notification
#        Notification().notify(torrent_id)
