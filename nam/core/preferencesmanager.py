#
# preferencesmanager.py
#
# Copyright (C) 2008-2010 Andrew Resch <andrewresch@gmail.com>
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


import os
import logging
import threading
import pkg_resources
from twisted.internet import reactor
from twisted.internet.task import LoopingCall

from nam.event import *
import nam.configmanager
import nam.common
import nam.component as component

log = logging.getLogger(__name__)

DEFAULT_PREFS = {
    "send_info": False,
    "daemon_port": 56746,
    "allow_remote": False,
    "plugins_location": os.path.join(nam.configmanager.get_config_dir(), "plugins"),
    "enabled_plugins": [],
    "new_release_check": True,
    "cache_size": 512,
    "cache_expiry": 60,
    "db": {
        "name": "nam.sqlite",
        "host": "",
        "path": nam.configmanager.get_config_dir(),
        "user": "",
        "pass": "",
        "engine": "sqlite"
    }
}

class PreferencesManager(component.Component):
    def __init__(self):
        component.Component.__init__(self, "PreferencesManager")

        self.config = nam.configmanager.ConfigManager("core.conf", DEFAULT_PREFS)

    def start(self):
        self.core = component.get("Core")
        self.new_release_timer = None

        # Set the initial preferences on start-up
        for key in DEFAULT_PREFS:
            self.do_config_set_func(key, self.config[key])

        self.config.register_change_callback(self._on_config_value_change)

    def stop(self):
        if self.new_release_timer:
            self.new_release_timer.stop()

    # Config set functions
    def do_config_set_func(self, key, value):
        on_set_func = getattr(self, "_on_set_" + key, None)
        if on_set_func:
            on_set_func(key, value)

    def _on_config_value_change(self, key, value):
        self.do_config_set_func(key, value)
        component.get("EventManager").emit(ConfigValueChangedEvent(key, value))

    def _on_set_new_release_check(self, key, value):
        if value:
            log.debug("Checking for new release..")
            threading.Thread(target=self.core.get_new_release).start()
            if self.new_release_timer:
                self.new_release_timer.stop()
            # Set a timer to check for a new release every 3 days
            self.new_release_timer = LoopingCall(
                self._on_set_new_release_check, "new_release_check", True)
            self.new_release_timer.start(72 * 60 * 60, False)
        else:
            if self.new_release_timer:
                self.new_release_timer.stop()
