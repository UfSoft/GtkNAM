#
# daemon.py
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

import os
import gettext
import locale
import logging
import pkg_resources

import pygst
pygst.require("0.10")

import gobject
gobject.threads_init()

#from twisted.internet import gtk2reactor
#gtk2reactor.install()

from twisted.python import threadable
threadable.init()

from twisted.internet import reactor
import twisted.internet.error

import nam.component as component
import nam.configmanager
import nam.common
from nam.core.rpcserver import RPCServer, export
import nam.error

log = logging.getLogger(__name__)

class Daemon(object):
    def __init__(self, options=None, args=None, classic=False):
        # Check for another running instance of the daemon
        if os.path.isfile(nam.configmanager.get_config_dir("nam.pid")):
            # Get the PID and the port of the supposedly running daemon
            try:
                (pid, port) = open(
                    nam.configmanager.get_config_dir("nam.pid")
                ).read().strip().split(";")
                pid = int(pid)
                port = int(port)
            except ValueError:
                pid = None
                port = None


            def process_running(pid):
                if nam.common.windows_check():
                    # Do some fancy WMI junk to see if the PID exists in Windows
                    from win32com.client import GetObject
                    def get_proclist():
                        WMI = GetObject('winmgmts:')
                        processes = WMI.InstancesOf('Win32_Process')
                        return [process.Properties_('ProcessID').Value for process in processes]
                    return pid in get_proclist()
                else:
                    # We can just use os.kill on UNIX to test if the process is running
                    try:
                        os.kill(pid, 0)
                    except OSError:
                        return False
                    else:
                        return True

            if pid is not None and process_running(pid):
                # Ok, so a process is running with this PID, let's make doubly-sure
                # it's a deluged process by trying to open a socket to it's port.
                import socket
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    s.connect(("127.0.0.1", port))
                except socket.error:
                    # Can't connect, so it must not be a deluged process..
                    pass
                else:
                    # This is a deluged!
                    s.close()
                    raise nam.error.DaemonRunningError(
                        "There is a nam-daemon running with this config directory!"
                    )

        # Twisted catches signals to terminate, so just have it call the shutdown
        # method.
        reactor.addSystemEventTrigger("after", "shutdown", self.shutdown)

        # Catch some Windows specific signals
        if nam.common.windows_check():
            from win32api import SetConsoleCtrlHandler
            from win32con import CTRL_CLOSE_EVENT
            from win32con import CTRL_SHUTDOWN_EVENT
            def win_handler(ctrl_type):
                log.debug("ctrl_type: %s", ctrl_type)
                if ctrl_type == CTRL_CLOSE_EVENT or ctrl_type == CTRL_SHUTDOWN_EVENT:
                    self.__shutdown()
                    return 1
            SetConsoleCtrlHandler(win_handler)

        version = nam.common.get_version()

        log.info("NAM daemon %s", version)
        log.debug("options: %s", options)
        log.debug("args: %s", args)
        # Set the config directory
        if options and options.config:
            nam.configmanager.set_config_dir(options.config)

        from nam.core.core import Core
        # Start the core as a thread and join it until it's done
        self.core = Core()

        port = self.core.config["daemon_port"]
        if options and options.port:
            port = options.port
        if options and options.ui_interface:
            interface = options.ui_interface
        else:
            interface = ""

        self.rpcserver = RPCServer(
            port=port,
            allow_remote=self.core.config["allow_remote"],
            listen=not classic,
            interface=interface
        )

        # Register the daemon and the core RPCs
        self.rpcserver.register_object(self.core)
        self.rpcserver.register_object(self)


        # Make sure we start the PreferencesManager first
        component.start("PreferencesManager")
#        component.start("EventManager")
        component.start("DatabaseManager")
#        component.start("SourcesManager")

        if not classic:
            # Write out a pid file all the time, we use this to see if a deluged
            # is running.
            # We also include the running port number to do an additional test
            open(nam.configmanager.get_config_dir("nam.pid"), "wb").write(
                "%s;%s\n" % (os.getpid(), port)
            )

            component.start()
            try:
                reactor.run()
            finally:
                self._shutdown()

    @export()
    def shutdown(self, *args, **kwargs):
        reactor.callLater(0, reactor.stop)

    def _shutdown(self, *args, **kwargs):
        try:
            os.remove(nam.configmanager.get_config_dir("nam.pid"))
        except Exception, e:
            log.exception(e)
            log.error("Error removing nam.pid!")

        component.shutdown()
        try:
            reactor.stop()
        except twisted.internet.error.ReactorNotRunning:
            log.debug("Tried to stop the reactor but it is not running..")

    @export()
    def info(self):
        """
        Returns some info from the daemon.

        :returns: str, the version number
        """
        return nam.common.get_version()

    @export()
    def get_method_list(self):
        """
        Returns a list of the exported methods.
        """
        return self.rpcserver.get_method_list()
