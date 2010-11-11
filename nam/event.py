#
# event.py
#
# Copyright (C) 2009 Andrew Resch <andrewresch@gmail.com>
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
#   The Free Software Foundation, Inc.,
#   51 Franklin Street, Fifth Floor
#   Boston, MA  02110-1301, USA.
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

"""
Event module.

This module describes the types of events that can be generated by the daemon
and subsequently emitted to the clients.

"""

known_events = {}

class NAMEventMetaClass(type):
    """
    This metaclass simply keeps a list of all events classes created.
    """
    def __init__(cls, name, bases, dct):
        super(NAMEventMetaClass, cls).__init__(name, bases, dct)
        if name != "NAMEvent":
            known_events[name] = cls

class NAMEvent(object):
    """
    The base class for all events.

    :prop name: this is the name of the class which is in-turn the event name
    :prop args: a list of the attribute values

    """
    __metaclass__ = NAMEventMetaClass

    def _get_name(self):
        return self.__class__.__name__

    def _get_args(self):
        if not hasattr(self, "_args"):
            return []
        return self._args

    name = property(fget=_get_name)
    args = property(fget=_get_args)

class NewVersionAvailableEvent(NAMEvent):
    """
    Emitted when a more recent version of NAM is available.
    """
    def __init__(self, new_release):
        """
        :param new_release: str, the new version that is available
        """
        self._args = [new_release]

class SessionStartedEvent(NAMEvent):
    """
    Emitted when a session has started.  This typically only happens once when
    the daemon is initially started.
    """
    pass

class SessionPausedEvent(NAMEvent):
    """
    Emitted when the session has been paused.
    """
    pass

class SessionResumedEvent(NAMEvent):
    """
    Emitted when the session has been resumed.
    """
    pass

class ConfigValueChangedEvent(NAMEvent):
    """
    Emitted when a config value changes in the Core.
    """
    def __init__(self, key, value):
        """
        :param key: str, the key that changed
        :param value: the new value of the `:param:key`
        """
        self._args = [key, value]

class PluginEnabledEvent(NAMEvent):
    """
    Emitted when a plugin is enabled in the Core.
    """
    def __init__(self, name):
        """
        :param name: the plugin name
        :type name: string
        """
        self._args = [name]

class PluginDisabledEvent(NAMEvent):
    """
    Emitted when a plugin is disabled in the Core.
    """
    def __init__(self, name):
        """
        :param name: the plugin name
        :type name: string
        """
        self._args = [name]

class DatabaseUpgradeRequired(NAMEvent):
    pass

class DatabaseUpgradeStart(NAMEvent):
    pass

class DatabaseUpgradeComplete(NAMEvent):
    pass

class SourceAdded(NAMEvent):
    """
    Emitted when new audio source is added.
    """

    def __init__(self, source):
        """
        :param id: the source id
        :type id: int
        :param name: the source name
        :type name: string
        """
        self._args = [source]

class SourceUpdate(NAMEvent):
    """
    Emitted when new audio source is added.
    """

    def __init__(self, source_id, updated_details):
        """
        :param id: the source id
        :type id: int
        :param name: the source name
        :type name: string
        """
        self._args = [source_id, updated_details]

class SourceUpdated(NAMEvent):
    """
    Emitted when new audio source is added.
    """

    def __init__(self, source_id):
        """
        :param id: the source id
        :type id: int
        :param name: the source name
        :type name: string
        """
        self._args = [source_id]

class SourceRemoved(NAMEvent):
    """
    Emitted when new audio source is added.
    """

    def __init__(self, source_id):
        """
        :param id: the source id
        :type id: int
        :param name: the source name
        :type name: string
        """
        self._args = [source_id]

class SourceLoaded(NAMEvent):
    """
    Emitted when an audio source is loaded from db.
    """

    def __init__(self, source_id):
        """
        :param id: the source id
        :type id: int
        :param name: the source name
        :type name: string
        """
        self._args = [source_id]

#class SourceEnabled(NAMEvent):
#    """
#    Emitted when an audio source is loaded from db.
#    """
#
#    def __init__(self, source_id):
#        """
#        :param id: the source id
#        :type id: int
#        :param name: the source name
#        :type name: string
#        """
#        self._args = [source_id]
#
#class SourceDisabled(NAMEvent):
#    """
#    Emitted when an audio source is loaded from db.
#    """
#
#    def __init__(self, source_id):
#        """
#        :param id: the source id
#        :type id: int
#        :param name: the source name
#        :type name: string
#        """
#        self._args = [source_id]


class SourceBufferingEvent(NAMEvent):
    """
    Emitted when an audio source is loaded from db.
    """

    def __init__(self, source, percent):
        """
        :param id: the source id
        :type id: int
        :param name: the source name
        :type name: string
        """
        self._args = [source, percent]

class SourceBufferedEvent(NAMEvent):
    """
    Emitted when an audio source is loaded from db.
    """

    def __init__(self, source):
        """
        :param id: the source id
        :type id: int
        :param name: the source name
        :type name: string
        """
        self._args = [source]

class SourcePlay(NAMEvent):
    """
    Emitted when an audio source is loaded from db.
    """

    def __init__(self, source):
        """
        :param id: the source id
        :type id: int
        :param name: the source name
        :type name: string
        """
        self._args = [source]

class SourcePlaying(NAMEvent):
    """
    Emitted when an audio source is loaded from db.
    """

    def __init__(self, source):
        """
        :param id: the source id
        :type id: int
        :param name: the source name
        :type name: string
        """
        self._args = [source]

class SourcePause(NAMEvent):
    """
    Emitted when an audio source is loaded from db.
    """

    def __init__(self, source):
        """
        :param id: the source id
        :type id: int
        :param name: the source name
        :type name: string
        """
        self._args = [source]

class SourcePaused(NAMEvent):
    """
    Emitted when an audio source is loaded from db.
    """

    def __init__(self, source):
        """
        :param id: the source id
        :type id: int
        :param name: the source name
        :type name: string
        """
        self._args = [source]

class SourceStop(NAMEvent):
    """
    Emitted when an audio source is loaded from db.
    """

    def __init__(self, source):
        """
        :param id: the source id
        :type id: int
        :param name: the source name
        :type name: string
        """
        self._args = [source]


class SourceStopped(NAMEvent):
    """
    Emitted when an audio source is loaded from db.
    """

    def __init__(self, source):
        """
        :param id: the source id
        :type id: int
        :param name: the source name
        :type name: string
        """
        self._args = [source]

class SourceExists(NAMEvent):
    """
    Emitted when new audio source is added.
    """

    def __init__(self, message):
        """
        :param name: the message
        :type name: string
        """
        self._args = [message]

class SourceDoesNotExist(NAMEvent):

    def __init__(self, message):
        """
        :param name: the message
        :type name: string
        """
        self._args = [message]

#class AudioAlertPlay(NAMEvent):
#    def __init__(self):
#        pass
#
#class AudioAlertPlaying(NAMEvent):
#    def __init__(self):
#        pass
#
#class AudioAlertStop(NAMEvent):
#    def __init__(self):
#        pass
#
#class AudioAlertStopped(NAMEvent):
#    def __init__(self):
#        pass
