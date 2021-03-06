#
# gtkui.py
#
# Copyright (C) 2007-2009 Andrew Resch <andrewresch@gmail.com>
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



# Install the twisted reactor
from twisted.internet import gtk2reactor
reactor = gtk2reactor.install()
from twisted.python import threadable

import gobject
gobject.threads_init()

# This needs to be done pretty early
from nam.utils.logger import set_loglevel, setup_logging
setup_logging()

#import gettext
#import locale
import pkg_resources
import gtk, gtk.glade
import logging
import sys

import __builtin__
__builtin__.__dict__["_"] = lambda x: x

log = logging.getLogger(__name__)

## Initialize gettext
#try:
#    if hasattr(locale, "bindtextdomain"):
#        locale.bindtextdomain("deluge", pkg_resources.resource_filename("deluge", "i18n"))
#    if hasattr(locale, "textdomain"):
#        locale.textdomain("deluge")
#    gettext.bindtextdomain("deluge", pkg_resources.resource_filename("deluge", "i18n"))
#    gettext.textdomain("deluge")
#    gettext.install("deluge", pkg_resources.resource_filename("deluge", "i18n"))
#    gtk.glade.bindtextdomain("deluge", pkg_resources.resource_filename("deluge", "i18n"))
#    gtk.glade.textdomain("deluge")
#except Exception, e:
#    log.error("Unable to initialize gettext/locale!")
#    log.exception(e)
#    import __builtin__
#    __builtin__.__dict__["_"] = lambda x: x

import nam.component as component
from nam.ui.client import client
from nam.ui.gtkui.mainwindow import MainWindow
#from menubar import MenuBar
#from toolbar import ToolBar
#from torrentview import TorrentView
#from torrentdetails import TorrentDetails
#from sidebar import SideBar
#from filtertreeview import FilterTreeView
#from preferences import Preferences
#from nam.ui.gtkui.systemtray import SystemTray
#from statusbar import StatusBar
from connectionmanager import ConnectionManager
from pluginmanager import PluginManager
#from ipcinterface import IPCInterface
#from deluge.ui.tracker_icons import TrackerIcons
#from queuedtorrents import QueuedTorrents
#from addtorrentdialog import AddTorrentDialog
#from deluge.ui.sessionproxy import SessionProxy

from nam.ui.gtkui import dialogs
from nam.ui.gtkui import common
from nam.ui.gtkui.messagesview import MessagesView
from nam.ui.gtkui.audioplayer import AudioPlayer
from nam.ui.gtkui.sourcesview import SourcesView
from nam.ui.gtkui.sourcesmanager import SourcesManager
from nam.ui.gtkui.statusbar import StatusBar
from nam.ui.gtkui.toolbar import ToolBar

import nam.configmanager
import nam.common
import nam.error

from nam.ui.ui import _UI

class Gtk(_UI):

    help = """Starts the Deluge GTK+ interface"""

    def __init__(self):
        super(Gtk, self).__init__("gtk")

    def start(self):
        super(Gtk, self).start()

        GtkUI(self.args)

def start():
    Gtk().start()

start_ui = start

DEFAULT_PREFS = {
    "classic_mode": True,
#    "interactive_add": True,
    "focus_add_dialog": True,
    "enable_system_tray": True,
    "close_to_tray": True,
    "start_in_tray": False,
#    "lock_tray": False,
#    "tray_password": "",
    "check_new_releases": True,
    "default_load_path": None,
    "window_maximized": False,
    "window_x_pos": 0,
    "window_y_pos": 0,
    "window_width": 800,
    "window_height": 600,
    "window_hpane_position": 570,
#    "tray_download_speed_list" : [5.0, 10.0, 30.0, 80.0, 300.0],
#    "tray_upload_speed_list" : [5.0, 10.0, 30.0, 80.0, 300.0],
#    "connection_limit_list": [50, 100, 200, 300, 500],
    "enabled_plugins": [],
    "show_connection_manager_on_start": True,
    "autoconnect": False,
    "autoconnect_host_id": None,
    "autostart_localhost": False,
#    "autoadd_queued": False,
#    "autoadd_enable": False,
#    "autoadd_location": "",
    #"choose_directory_dialog_path": nam.common.get_default_download_dir(),
    "show_new_releases": True,
    "signal_port": 40000,
#    "ntf_tray_blink": True,
#    "ntf_sound": False,
#    #"ntf_sound_path": nam.common.get_default_download_dir(),
#    "ntf_popup": False,
#    "ntf_email": False,
#    "ntf_email_add": "",
#    "ntf_username": "",
#    "ntf_pass": "",
#    "ntf_server": "",
#    "ntf_security": None,
    "signal_port": 40000,
    "show_sidebar": True,
    "show_toolbar": True,
    "show_statusbar": True,
#    "sidebar_show_zero": False,
#    "sidebar_show_trackers": True,
    "sidebar_position": 170,
#    "show_rate_in_title": False,
#    "createtorrent.trackers": []
    "sourcesmanager": {
        "window_maximized": False,
        "window_x_pos": 0,
        "window_y_pos": 0,
        "window_width": 450,
        "window_height": 350,
    }
}

class GtkUI(object):
    def __init__(self, args):
        self.daemon_bps = (0,0,0)
        # Setup signals
        try:
            import gnome.ui
            import gnome
            self.gnome_prog = gnome.init("NetworkAudioMonitor",
                                         nam.common.get_version())
            self.gnome_client = gnome.ui.master_client()
            def on_die(*args):
                reactor.stop()
            self.gnome_client.connect("die", on_die)
            log.debug("GNOME session 'die' handler registered!")
        except Exception, e:
            log.warning("Unable to register a 'die' handler with the GNOME session manager: %s", e)

        if nam.common.windows_check():
            from win32api import SetConsoleCtrlHandler
            from win32con import CTRL_CLOSE_EVENT
            from win32con import CTRL_SHUTDOWN_EVENT
            def win_handler(ctrl_type):
                log.debug("ctrl_type: %s", ctrl_type)
                if ctrl_type in (CTRL_CLOSE_EVENT, CTRL_SHUTDOWN_EVENT):
                    reactor.stop()
                    return 1
            SetConsoleCtrlHandler(win_handler)

        # Make sure gtkui.conf has at least the defaults set
        self.config = nam.configmanager.ConfigManager("gtkui.conf", DEFAULT_PREFS)

        # We need to check on exit if it was started in classic mode to ensure we
        # shutdown the daemon.
        self.started_in_classic = self.config["classic_mode"]

        # Initialize gdk threading
        gtk.gdk.threads_init()
        gobject.threads_init()
        # Initialize twisted threads
        threadable.init()

        # We make sure that the UI components start once we get a core URI
        client.add_disconnect_callback(self.__on_disconnect)

#        self.trackericons = TrackerIcons()
#        self.sessionproxy = SessionProxy()
        # Initialize various components of the gtkui
        self.mainwindow = MainWindow()
#        self.menubar = MenuBar()
#        self.toolbar = ToolBar()
#        self.torrentview = TorrentView()
#        self.torrentdetails = TorrentDetails()
#        self.sidebar = SideBar()
#        self.filtertreeview = FilterTreeView()
#        self.preferences = Preferences()
#        self.systemtray = SystemTray()
#        self.statusbar = StatusBar()
#        self.addtorrentdialog = AddTorrentDialog()
        self.audioplayer = AudioPlayer()
        self.sourcesview = SourcesView()
        self.sourcesmanager = SourcesManager()
        self.messagesview = MessagesView()
        self.statusbar = StatusBar()
        self.toolbar = ToolBar()

        # Initalize the plugins
        self.plugins = PluginManager()

        # Show the connection manager
        self.connectionmanager = ConnectionManager()

        from twisted.internet.task import LoopingCall
        rpc_stats = LoopingCall(self.print_rpc_stats)
        rpc_stats.start(15)
        update_rpc_stats = LoopingCall(self.update_rpc_stats)
        update_rpc_stats.start(1)

        reactor.callWhenRunning(self._on_reactor_start)
#        reactor.callWhenRunning(self.audioplayer.start)
        # Start the gtk main loop
        gtk.gdk.threads_enter()
        reactor.run()
        self.shutdown()
        gtk.gdk.threads_leave()

    def shutdown(self, *args, **kwargs):
        log.debug("gtkui shutting down..")

        component.stop()

        # Process any pending gtk events since the mainloop has been quit
        if not nam.common.windows_check():
            while gtk.events_pending() and reactor.running:
                reactor.doIteration(0)

        # Shutdown all components
        component.shutdown()

        # Make sure the config is saved.
        self.config.save()

    def update_rpc_stats(self, debug_log=False):
        self.print_rpc_stats(False)

    def print_rpc_stats(self, debug_log=True):
        import time
        try:
            recv = client.get_bytes_recv()
            sent = client.get_bytes_sent()
        except AttributeError:
            return

        if debug_log:
            log.debug("sent: %s recv: %s", nam.common.fsize(sent),
                      nam.common.fsize(recv))
        t = time.time()
        delta_time = t - self.daemon_bps[0]
        delta_sent = sent - self.daemon_bps[1]
        delta_recv = recv - self.daemon_bps[2]

        sent_rate = nam.common.fspeed(float(delta_sent) / float(delta_time))
        recv_rate = nam.common.fspeed(float(delta_recv) / float(delta_time))
        if debug_log:
            log.debug("sent rate: %s recv rate: %s", sent_rate, recv_rate)
        self.daemon_bps = (t, sent, recv)
        if not hasattr(self.statusbar, "traffic_item"):
            return
        self.statusbar.traffic_item.set_text(
            "%s / %s (%s / %s)" % (recv_rate, sent_rate, nam.common.fsize(recv),
                                   nam.common.fsize(sent))
        )

    def _on_reactor_start(self):
        log.debug("_on_reactor_start")
        self.mainwindow.first_show()

        if self.config["classic_mode"]:

            def on_dialog_response(response):
                if response != gtk.RESPONSE_YES:
                    # The user does not want to turn Classic Mode off, so just quit
                    reactor.stop()
                    return
                # Turning off classic_mode
                self.config["classic_mode"] = False
                self.__start_non_classic()

            try:
                client.start_classic_mode()
            except nam.error.DaemonRunningError:
                d = dialogs.YesNoDialog(
                    _("Turn off Classic Mode?"),
                    _("It appears that a NAM daemon process (nam-daemon) is already running.\n\n\
You will either need to stop the daemon or turn off Classic Mode to continue.")).run()

                self.started_in_classic = False
                d.addCallback(on_dialog_response)
            except Exception, e:
                import traceback
                tb = sys.exc_info()
                ed = dialogs.ErrorDialog(
                    _("Error Starting Core"),
                    _("There was an error starting the core component which is required to run NAM in Classic Mode.\n\n\
Please see the details below for more information."), details=traceback.format_exc(tb[2])).run()
                def on_ed_response(response):
                    d = dialogs.YesNoDialog(
                        _("Turn off Classic Mode?"),
                        _("Since there was an error starting in Classic Mode would you like to continue by turning it off?")).run()
                    self.started_in_classic = False
                    d.addCallback(on_dialog_response)
                ed.addCallback(on_ed_response)
            else:
                component.start()
                return

        else:
            self.__start_non_classic()

    def __start_non_classic(self):
            # Autoconnect to a host
            if self.config["autoconnect"]:
                for host in self.connectionmanager.config["hosts"]:
                    if host[0] == self.config["autoconnect_host_id"]:
                        try_connect = True
                        # Check to see if we need to start the localhost daemon
                        if self.config["autostart_localhost"] and host[1] in ("localhost", "127.0.0.1"):
                            log.debug("Autostarting localhost:%s", host[2])
                            try_connect = client.start_daemon(host[2], nam.configmanager.get_config_dir())
                            log.debug("Localhost started: %s", try_connect)
                            if not try_connect:
                                dialogs.ErrorDialog(
                                    _("Error Starting Daemon"),
                                    _("There was an error starting the daemon process.  Try running it from a console to see if there is an error.")).run()

                        def on_connect(connector):
                            component.start()
                        def on_connect_fail(result, try_counter):
                            log.error("Connection to host failed..")
                            # We failed connecting to the daemon, but lets try again
                            if try_counter:
                                log.info("Retrying connection.. Retries left: %s", try_counter)
                                try_counter -= 1
                                import time
                                time.sleep(0.5)
                                do_connect(try_counter)
                            return result

                        def do_connect(try_counter):
                            client.connect(*host[1:]).addCallback(on_connect).addErrback(on_connect_fail, try_counter)

                        if try_connect:
                            do_connect(6)
                        break

            if self.config["show_connection_manager_on_start"]:
                # XXX: We need to call a simulate() here, but this could be a bug in twisted
                reactor.simulate()
                self.connectionmanager.show()


    def __on_disconnect(self):
        """
        Called when disconnected from the daemon.  We basically just stop all
        the components here.
        """
        component.stop()
