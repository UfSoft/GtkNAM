#
# core.py
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
#     The Free Software Foundation, Inc.,
#     51 Franklin Street, Fifth Floor
#     Boston, MA  02110-1301, USA.
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

#from deluge._libtorrent import lt

import os
import glob
import base64
import shutil
import threading
import pkg_resources
import warnings
import logging


from twisted.internet import reactor, defer
from twisted.internet.task import LoopingCall
import twisted.web.client

#from deluge.httpdownloader import download_file


import nam.configmanager
import nam.common
import nam.component as component
from nam.event import *
from nam.error import *
from nam.core.databasemanager import DatabaseManager
from nam.core.pluginmanager import PluginManager
from nam.core.preferencesmanager import PreferencesManager
from nam.core.authmanager import AuthManager
from nam.core.eventmanager import EventManager
from nam.core.sourcesmanager import SourcesManager
from nam.core.rpcserver import export
from nam.database import AUTH_LEVEL_ADMIN, MessageKind

log = logging.getLogger(__name__)

class Core(component.Component):
    def __init__(self, listen_interface=None):
        log.debug("Core init..")
        component.Component.__init__(self, "Core")

        # Create the components
        self.eventmanager = EventManager()
        self.preferencesmanager = PreferencesManager()
        self.databasemanager = DatabaseManager()
        self.pluginmanager = PluginManager(self)
        self.authmanager = AuthManager()
        self.sourcesmanager = SourcesManager()

        # New release check information
        self.new_release = None

        # Get the core config
        self.config = nam.configmanager.ConfigManager("core.conf")

        # If there was an interface value from the command line, use it, but
        # store the one in the config so we can restore it on shutdown
        self.__old_interface = None
        if listen_interface:
            self.__old_interface = self.config["listen_interface"]
            self.config["listen_interface"] = listen_interface

    def start(self):
        """Starts the core"""
        # New release check information
        self.__new_release = None

    def stop(self):
        # We stored a copy of the old interface value
        if self.__old_interface:
            self.config["listen_interface"] = self.__old_interface

        # Make sure the config file has been saved
        self.config.save()

    def shutdown(self):
        pass

    def get_new_release(self):
        log.debug("get_new_release")
        from urllib2 import urlopen
        try:
            self.new_release = urlopen(
                "http://download.deluge-torrent.org/version-1.0").read().strip()
        except Exception, e:
            log.debug("Unable to get release info from website: %s", e)
            return
        self.check_new_release()

    def check_new_release(self):
        if self.new_release:
            log.debug("new_release: %s", self.new_release)
            if nam.common.VersionSplit(self.new_release) > nam.common.VersionSplit(nam.common.get_version()):
                component.get("EventManager").emit(NewVersionAvailableEvent(self.new_release))
                return self.new_release
        return False

    # Exported Methods
    # Accounts
    @export(AUTH_LEVEL_ADMIN)
    def add_account(self, username, display_name, password, access_level):
        self.authmanager.add_account(username, display_name, password, access_level)

    @export(AUTH_LEVEL_ADMIN)
    def remove_account(self, username):
        self.authmanager.remove_account(username)

    @export(AUTH_LEVEL_ADMIN)
    def alter_account(self, username, display_name, password, access_level):
        self.authmanager.alter_account(username, display_name, password, access_level)

    # Sources
    @export(AUTH_LEVEL_ADMIN)
    def add_source(self, name, uri):
        self.sourcesmanager.add_source(name, uri)

    @export(AUTH_LEVEL_ADMIN)
    def remove_source(self, id):
        self.sourcesmanager.add_remove(id)

    @export(AUTH_LEVEL_ADMIN)
    def alter_source(self, id, name, uri):
        self.sourcesmanager.alter_source(id, name, uri)

    @export
    def get_source(self, id):
        return self.sourcesmanager.get_source(id)

    @export
    def get_source_details(self, id):
        return self.sourcesmanager.get_source_details(id)

    @export
    def get_sources_list(self, disabled=False):
        return self.sourcesmanager.get_sources_list(disabled)

    @export
    def get_message_kinds(self):
        session = component.get("DatabaseManager").session()
        message_kinds = []
        for kind in session.query(MessageKind).all():
            message_kinds.append({'id': kind.id, 'kind': kind.kind})
        return message_kinds

    @export
    def play_source(self, source_id):
        log.debug("\n\n\nPlay Button Clicked on %s\n\n", source_id)
        self.eventmanager.emit(SourcePlay(source_id))

    @export()
    def stop_source(self, source_id):
        log.debug("\n\n\nStop Button Clicked on %s", source_id)
        self.eventmanager.emit(SourceStop(source_id))

#    @export
#    def add_torrent_file(self, filename, filedump, options):
#        """
#        Adds a torrent file to the session.
#
#        :param filename: the filename of the torrent
#        :type filename: string
#        :param filedump:  a base64 encoded string of the torrent file contents
#        :type filedump: string
#        :param options: the options to apply to the torrent on add
#        :type options: dict
#
#        :returns: the torrent_id as a str or None
#        :rtype: string
#
#        """
#        try:
#            filedump = base64.decodestring(filedump)
#        except Exception, e:
#            log.error("There was an error decoding the filedump string!")
#            log.exception(e)
#
#        try:
#            torrent_id = self.torrentmanager.add(filedump=filedump, options=options, filename=filename)
#        except Exception, e:
#            log.error("There was an error adding the torrent file %s", filename)
#            log.exception(e)
#            torrent_id = None
#
#        return torrent_id
#
#    @export
#    def add_torrent_url(self, url, options, headers=None):
#        """
#        Adds a torrent from a url. Deluge will attempt to fetch the torrent
#        from url prior to adding it to the session.
#
#        :param url: the url pointing to the torrent file
#        :type url: string
#        :param options: the options to apply to the torrent on add
#        :type options: dict
#        :param headers: any optional headers to send
#        :type headers: dict
#
#        :returns: a Deferred which returns the torrent_id as a str or None
#        """
#        log.info("Attempting to add url %s", url)
#        def on_get_file(filename):
#            # We got the file, so add it to the session
#            data = open(filename, "rb").read()
#            return self.add_torrent_file(filename, base64.encodestring(data), options)
#
#        def on_get_file_error(failure):
#            # Log the error and pass the failure onto the client
#            log.error("Error occured downloading torrent from %s", url)
#            log.error("Reason: %s", failure.getErrorMessage())
#            return failure
#
#        d = download_file(url, url.split("/")[-1], headers=headers)
#        d.addCallback(on_get_file)
#        d.addErrback(on_get_file_error)
#        return d
#
#    @export
#    def add_torrent_magnet(self, uri, options):
#        """
#        Adds a torrent from a magnet link.
#
#        :param uri: the magnet link
#        :type uri: string
#        :param options: the options to apply to the torrent on add
#        :type options: dict
#
#        :returns: the torrent_id
#        :rtype: string
#
#        """
#        log.debug("Attempting to add by magnet uri: %s", uri)
#
#        return self.torrentmanager.add(magnet=uri, options=options)
#
#    @export
#    def remove_torrent(self, torrent_id, remove_data):
#        """
#        Removes a torrent from the session.
#
#        :param torrent_id: the torrent_id of the torrent to remove
#        :type torrent_id: string
#        :param remove_data: if True, remove the data associated with this torrent
#        :type remove_data: boolean
#        :returns: True if removed successfully
#        :rtype: bool
#
#        :raises InvalidTorrentError: if the torrent_id does not exist in the session
#
#        """
#        log.debug("Removing torrent %s from the core.", torrent_id)
#        return self.torrentmanager.remove(torrent_id, remove_data)
#
#    @export
#    def get_session_status(self, keys):
#        """
#        Gets the session status values for 'keys', these keys are taking
#        from libtorrent's session status.
#
#        See: http://www.rasterbar.com/products/libtorrent/manual.html#status
#
#        :param keys: the keys for which we want values
#        :type keys: list
#        :returns: a dictionary of {key: value, ...}
#        :rtype: dict
#
#        """
#        status = {}
#        session_status = self.session.status()
#        for key in keys:
#            status[key] = getattr(session_status, key)
#
#        return status
#
#    @export
#    def get_cache_status(self):
#        """
#        Returns a dictionary of the session's cache status.
#
#        :returns: the cache status
#        :rtype: dict
#
#        """
#
#        status = self.session.get_cache_status()
#        cache = {}
#        for attr in dir(status):
#            if attr.startswith("_"):
#                continue
#            cache[attr] = getattr(status, attr)
#
#        # Add in a couple ratios
#        try:
#            cache["write_hit_ratio"] = float((cache["blocks_written"] - cache["writes"])) / float(cache["blocks_written"])
#        except ZeroDivisionError:
#            cache["write_hit_ratio"] = 0.0
#
#        try:
#            cache["read_hit_ratio"] = float(cache["blocks_read_hit"]) / float(cache["blocks_read"])
#        except ZeroDivisionError:
#            cache["read_hit_ratio"] = 0.0
#
#        return cache
#
#    @export
#    def force_reannounce(self, torrent_ids):
#        log.debug("Forcing reannouncment to: %s", torrent_ids)
#        for torrent_id in torrent_ids:
#            self.torrentmanager[torrent_id].force_reannounce()
#
#    @export
#    def pause_torrent(self, torrent_ids):
#        log.debug("Pausing: %s", torrent_ids)
#        for torrent_id in torrent_ids:
#            if not self.torrentmanager[torrent_id].pause():
#                log.warning("Error pausing torrent %s", torrent_id)
#
#    @export
#    def connect_peer(self, torrent_id, ip, port):
#        log.debug("adding peer %s to %s", ip, torrent_id)
#        if not self.torrentmanager[torrent_id].connect_peer(ip, port):
#            log.warning("Error adding peer %s:%s to %s", ip, port, torrent_id)
#
#    @export
#    def move_storage(self, torrent_ids, dest):
#        log.debug("Moving storage %s to %s", torrent_ids, dest)
#        for torrent_id in torrent_ids:
#            if not self.torrentmanager[torrent_id].move_storage(dest):
#                log.warning("Error moving torrent %s to %s", torrent_id, dest)
#
#    @export
#    def pause_all_torrents(self):
#        """Pause all torrents in the session"""
#        for torrent in self.torrentmanager.torrents.values():
#            torrent.pause()
#
#    @export
#    def resume_all_torrents(self):
#        """Resume all torrents in the session"""
#        for torrent in self.torrentmanager.torrents.values():
#            torrent.resume()
#        component.get("EventManager").emit(SessionResumedEvent())
#
#    @export
#    def resume_torrent(self, torrent_ids):
#        log.debug("Resuming: %s", torrent_ids)
#        for torrent_id in torrent_ids:
#            self.torrentmanager[torrent_id].resume()
#
#    @export
#    def get_torrent_status(self, torrent_id, keys, diff=False):
#        # Build the status dictionary
#        status = self.torrentmanager[torrent_id].get_status(keys, diff)
#
#        # Get the leftover fields and ask the plugin manager to fill them
#        leftover_fields = list(set(keys) - set(status.keys()))
#        if len(leftover_fields) > 0:
#            status.update(self.pluginmanager.get_status(torrent_id, leftover_fields))
#        return status
#
#    @export
#    def get_torrents_status(self, filter_dict, keys, diff=False):
#        """
#        returns all torrents , optionally filtered by filter_dict.
#        """
#        torrent_ids = self.filtermanager.filter_torrent_ids(filter_dict)
#        status_dict = {}.fromkeys(torrent_ids)
#
#        # Get the torrent status for each torrent_id
#        for torrent_id in torrent_ids:
#            status_dict[torrent_id] = self.get_torrent_status(torrent_id, keys, diff)
#
#        return status_dict
#
#    @export
#    def get_filter_tree(self , show_zero_hits=True, hide_cat=None):
#        """
#        returns {field: [(value,count)] }
#        for use in sidebar(s)
#        """
#        return self.filtermanager.get_filter_tree(show_zero_hits, hide_cat)
#
#    @export
#    def get_session_state(self):
#        """Returns a list of torrent_ids in the session."""
#        # Get the torrent list from the TorrentManager
#        return self.torrentmanager.get_torrent_list()

    @export
    def get_config(self):
        """Get all the preferences as a dictionary"""
        return self.config.config

    @export
    def get_config_value(self, key):
        """Get the config value for key"""
        try:
            value = self.config[key]
        except KeyError:
            return None

        return value

    @export
    def get_config_values(self, keys):
        """Get the config values for the entered keys"""
        config = {}
        for key in keys:
            try:
                config[key] = self.config[key]
            except KeyError:
                pass
        return config

    @export
    def set_config(self, config):
        """Set the config with values from dictionary"""
        # Load all the values into the configuration
        for key in config.keys():
            if isinstance(config[key], basestring):
                config[key] = config[key].encode("utf8")
            self.config[key] = config[key]
#
#    @export
#    def get_listen_port(self):
#        """Returns the active listen port"""
#        return self.session.listen_port()
#
#    @export
#    def get_num_connections(self):
#        """Returns the current number of connections"""
#        return self.session.num_connections()

    @export
    def get_available_plugins(self):
        """Returns a list of plugins available in the core"""
        return self.pluginmanager.get_available_plugins()

    @export
    def get_enabled_plugins(self):
        """Returns a list of enabled plugins in the core"""
        return self.pluginmanager.get_enabled_plugins()

    @export
    def enable_plugin(self, plugin):
        self.pluginmanager.enable_plugin(plugin)
        return None

    @export
    def disable_plugin(self, plugin):
        self.pluginmanager.disable_plugin(plugin)
        return None

#    @export
#    def force_recheck(self, torrent_ids):
#        """Forces a data recheck on torrent_ids"""
#        for torrent_id in torrent_ids:
#            self.torrentmanager[torrent_id].force_recheck()
#
#    @export
#    def set_torrent_options(self, torrent_ids, options):
#        """Sets the torrent options for torrent_ids"""
#        for torrent_id in torrent_ids:
#            self.torrentmanager[torrent_id].set_options(options)
#
#    @export
#    def set_torrent_trackers(self, torrent_id, trackers):
#        """Sets a torrents tracker list.  trackers will be [{"url", "tier"}]"""
#        return self.torrentmanager[torrent_id].set_trackers(trackers)
#
#    @export
#    def set_torrent_max_connections(self, torrent_id, value):
#        """Sets a torrents max number of connections"""
#        return self.torrentmanager[torrent_id].set_max_connections(value)
#
#    @export
#    def set_torrent_max_upload_slots(self, torrent_id, value):
#        """Sets a torrents max number of upload slots"""
#        return self.torrentmanager[torrent_id].set_max_upload_slots(value)
#
#    @export
#    def set_torrent_max_upload_speed(self, torrent_id, value):
#        """Sets a torrents max upload speed"""
#        return self.torrentmanager[torrent_id].set_max_upload_speed(value)
#
#    @export
#    def set_torrent_max_download_speed(self, torrent_id, value):
#        """Sets a torrents max download speed"""
#        return self.torrentmanager[torrent_id].set_max_download_speed(value)
#
#    @export
#    def set_torrent_file_priorities(self, torrent_id, priorities):
#        """Sets a torrents file priorities"""
#        return self.torrentmanager[torrent_id].set_file_priorities(priorities)
#
#    @export
#    def set_torrent_prioritize_first_last(self, torrent_id, value):
#        """Sets a higher priority to the first and last pieces"""
#        return self.torrentmanager[torrent_id].set_prioritize_first_last(value)
#
#    @export
#    def set_torrent_auto_managed(self, torrent_id, value):
#        """Sets the auto managed flag for queueing purposes"""
#        return self.torrentmanager[torrent_id].set_auto_managed(value)
#
#    @export
#    def set_torrent_stop_at_ratio(self, torrent_id, value):
#        """Sets the torrent to stop at 'stop_ratio'"""
#        return self.torrentmanager[torrent_id].set_stop_at_ratio(value)
#
#    @export
#    def set_torrent_stop_ratio(self, torrent_id, value):
#        """Sets the ratio when to stop a torrent if 'stop_at_ratio' is set"""
#        return self.torrentmanager[torrent_id].set_stop_ratio(value)
#
#    @export
#    def set_torrent_remove_at_ratio(self, torrent_id, value):
#        """Sets the torrent to be removed at 'stop_ratio'"""
#        return self.torrentmanager[torrent_id].set_remove_at_ratio(value)
#
#    @export
#    def set_torrent_move_completed(self, torrent_id, value):
#        """Sets the torrent to be moved when completed"""
#        return self.torrentmanager[torrent_id].set_move_completed(value)
#
#    @export
#    def set_torrent_move_completed_path(self, torrent_id, value):
#        """Sets the path for the torrent to be moved when completed"""
#        return self.torrentmanager[torrent_id].set_move_completed_path(value)
#
#    @export
#    def get_path_size(self, path):
#        """Returns the size of the file or folder 'path' and -1 if the path is
#        unaccessible (non-existent or insufficient privs)"""
#        return deluge.common.get_path_size(path)
#
#    @export
#    def create_torrent(self, path, tracker, piece_length, comment, target,
#                        webseeds, private, created_by, trackers, add_to_session):
#
#        log.debug("creating torrent..")
#        threading.Thread(target=self._create_torrent_thread,
#            args=(
#                path,
#                tracker,
#                piece_length,
#                comment,
#                target,
#                webseeds,
#                private,
#                created_by,
#                trackers,
#                add_to_session)).start()
#
#    def _create_torrent_thread(self, path, tracker, piece_length, comment, target,
#                    webseeds, private, created_by, trackers, add_to_session):
#        import deluge.metafile
#        deluge.metafile.make_meta_file(
#            path,
#            tracker,
#            piece_length,
#            comment=comment,
#            target=target,
#            webseeds=webseeds,
#            private=private,
#            created_by=created_by,
#            trackers=trackers)
#        log.debug("torrent created!")
#        if add_to_session:
#            options = {}
#            options["download_location"] = os.path.split(path)[0]
#            self.add_torrent_file(os.path.split(target)[1], open(target, "rb").read(), options)

    @export
    def upload_plugin(self, filename, filedump):
        """This method is used to upload new plugins to the daemon.  It is used
        when connecting to the daemon remotely and installing a new plugin on
        the client side. 'plugin_data' is a xmlrpc.Binary object of the file data,
        ie, plugin_file.read()"""

        try:
            filedump = base64.decodestring(filedump)
        except Exception, e:
            log.error("There was an error decoding the filedump string!")
            log.exception(e)
            return

        f = open(os.path.join(nam.configmanager.get_config_dir(), "plugins", filename), "wb")
        f.write(filedump)
        f.close()
        component.get("CorePluginManager").scan_for_plugins()

    @export
    def rescan_plugins(self):
        """
        Rescans the plugin folders for new plugins
        """
        component.get("CorePluginManager").scan_for_plugins()

#    @export
#    def rename_files(self, torrent_id, filenames):
#        """
#        Rename files in torrent_id.  Since this is an asynchronous operation by
#        libtorrent, watch for the TorrentFileRenamedEvent to know when the
#        files have been renamed.
#
#        :param torrent_id: the torrent_id to rename files
#        :type torrent_id: string
#        :param filenames: a list of index, filename pairs
#        :type filenames: ((index, filename), ...)
#
#        :raises InvalidTorrentError: if torrent_id is invalid
#
#        """
#        if torrent_id not in self.torrentmanager.torrents:
#            raise InvalidTorrentError("torrent_id is not in session")
#
#        self.torrentmanager[torrent_id].rename_files(filenames)
#
#    @export
#    def rename_folder(self, torrent_id, folder, new_folder):
#        """
#        Renames the 'folder' to 'new_folder' in 'torrent_id'.  Watch for the
#        TorrentFolderRenamedEvent which is emitted when the folder has been
#        renamed successfully.
#
#        :param torrent_id: the torrent to rename folder in
#        :type torrent_id: string
#        :param folder: the folder to rename
#        :type folder: string
#        :param new_folder: the new folder name
#        :type new_folder: string
#
#        :raises InvalidTorrentError: if the torrent_id is invalid
#
#        """
#        if torrent_id not in self.torrentmanager.torrents:
#            raise InvalidTorrentError("torrent_id is not in session")
#
#        self.torrentmanager[torrent_id].rename_folder(folder, new_folder)
#
#    @export
#    def queue_top(self, torrent_ids):
#        log.debug("Attempting to queue %s to top", torrent_ids)
#        for torrent_id in torrent_ids:
#            try:
#                # If the queue method returns True, then we should emit a signal
#                if self.torrentmanager.queue_top(torrent_id):
#                    component.get("EventManager").emit(TorrentQueueChangedEvent())
#            except KeyError:
#                log.warning("torrent_id: %s does not exist in the queue", torrent_id)
#
#    @export
#    def queue_up(self, torrent_ids):
#        log.debug("Attempting to queue %s to up", torrent_ids)
#        #torrent_ids must be sorted before moving.
#        torrent_ids = list(torrent_ids)
#        torrent_ids.sort(key = lambda id: self.torrentmanager.torrents[id].get_queue_position())
#        for torrent_id in torrent_ids:
#            try:
#                # If the queue method returns True, then we should emit a signal
#                if self.torrentmanager.queue_up(torrent_id):
#                    component.get("EventManager").emit(TorrentQueueChangedEvent())
#            except KeyError:
#                log.warning("torrent_id: %s does not exist in the queue", torrent_id)
#
#    @export
#    def queue_down(self, torrent_ids):
#        log.debug("Attempting to queue %s to down", torrent_ids)
#        #torrent_ids must be sorted before moving.
#        torrent_ids = list(torrent_ids)
#        torrent_ids.sort(key = lambda id: -self.torrentmanager.torrents[id].get_queue_position())
#        for torrent_id in torrent_ids:
#            try:
#                # If the queue method returns True, then we should emit a signal
#                if self.torrentmanager.queue_down(torrent_id):
#                    component.get("EventManager").emit(TorrentQueueChangedEvent())
#            except KeyError:
#                log.warning("torrent_id: %s does not exist in the queue", torrent_id)
#
#    @export
#    def queue_bottom(self, torrent_ids):
#        log.debug("Attempting to queue %s to bottom", torrent_ids)
#        for torrent_id in torrent_ids:
#            try:
#                # If the queue method returns True, then we should emit a signal
#                if self.torrentmanager.queue_bottom(torrent_id):
#                    component.get("EventManager").emit(TorrentQueueChangedEvent())
#            except KeyError:
#                log.warning("torrent_id: %s does not exist in the queue", torrent_id)
#
#    @export
#    def glob(self, path):
#        return glob.glob(path)
#
#    @export
#    def test_listen_port(self):
#        """
#        Checks if the active port is open
#
#        :returns: True if the port is open, False if not
#        :rtype: bool
#
#        """
#        from twisted.web.client import getPage
#
#        d = getPage("http://deluge-torrent.org/test_port.php?port=%s" %
#                    self.get_listen_port(), timeout=30)
#
#        def on_get_page(result):
#            return bool(int(result))
#
#        d.addCallback(on_get_page)
#
#        return d
#
#    @export
#    def get_free_space(self, path=None):
#        """
#        Returns the number of free bytes at path
#
#        :param path: the path to check free space at, if None, use the default
#        download location
#        :type path: string
#
#        :returns: the number of free bytes at path
#        :rtype: int
#
#        :raises InvalidPathError: if the path is invalid
#
#        """
#        if not path:
#            path = self.config["download_location"]
#        try:
#            return nam.common.free_space(path)
#        except InvalidPathError:
#            return 0
#
#    @export
#    def get_libtorrent_version(self):
#        """
#        Returns the libtorrent version.
#
#        :returns: the version
#        :rtype: string
#
#        """
#        return lt.version
