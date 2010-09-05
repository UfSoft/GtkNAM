#
# new_release_dialog.py
#
# Copyright (C) 2008 Andrew Resch <andrewresch@gmail.com>
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
import gtk.glade
import pkg_resources
import nam.component as component
import nam.common
from nam.ui.gtkui import common
from nam.configmanager import ConfigManager

class NewReleaseDialog:
    def __init__(self):
        pass

    def show(self, available_version):
        self.config = ConfigManager("gtkui.conf")
        glade = gtk.glade.XML(pkg_resources.resource_filename(
            "nam.ui.gtkui", "glade/new_release_dialog.glade"
        ))
#        glade = component.get("MainWindow").main_glade
        self.dialog = glade.get_widget("new_release_dialog")
        self.dialog.set_icon(common.get_nam_icon())
        # Set the version labels
        glade.get_widget("image_new_release").set_from_file(
            nam.common.get_pixmap("nam-16.png")
        )
#        if nam.common.windows_check() or nam.common.osx_check():
#            glade.get_widget("image_new_release").set_from_file(
#                nam.common.get_pixmap("nam-16.png"))
#        else:
#            glade.get_widget("image_new_release").set_from_icon_name("nam", 4)
##            common.get_nam_icon()
#        glade.get_widget("image_new_release").set_from_file(
#            nam.common.get_pixmap("nam-16.png")
#        )

        glade.get_widget("label_available_version").set_text(available_version)
        glade.get_widget("label_current_version").set_text(
            nam.common.get_version())
        self.chk_not_show_dialog = glade.get_widget("chk_do_not_show_new_release")
        glade.get_widget("button_goto_downloads").connect(
            "clicked", self._on_button_goto_downloads)
        glade.get_widget("button_close_new_release").connect(
            "clicked", self._on_button_close_new_release)

        self.dialog.show_all()

    def _on_button_goto_downloads(self, widget):
        nam.common.open_url_in_browser("http://deluge-torrent.org")
        self.config["show_new_releases"] = not self.chk_not_show_dialog.get_active()
        self.dialog.destroy()

    def _on_button_close_new_release(self, widget):
        self.config["show_new_releases"] = not self.chk_not_show_dialog.get_active()
        self.dialog.destroy()

