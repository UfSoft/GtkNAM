#
# authmanager.py
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
import random
import stat
import logging

import nam.component as component
import nam.configmanager as configmanager
import nam.error

from nam.database import User

log = logging.getLogger(__name__)


class BadLoginError(nam.error.NAMError):
    pass

class AuthManager(component.Component):
    def __init__(self):
        component.Component.__init__(self, "AuthManager")

    def start(self):
        pass

    def stop(self):
        pass

    def shutdown(self):
        pass

    def authorize(self, username, password):
        """
        Authorizes users based on username and password

        :param username: str, username
        :param password: str, password
        :returns: int, the auth level for this user
        :rtype: int

        :raises BadLoginError: if the username does not exist or password does not match

        """

        session = component.get("DatabaseManager").session()

        account = session.query(User).get(username)
        if not account:
            raise BadLoginError("Username does not exist")

        if account.check_password(password):
            session.commit()
            return account.access_level
        else:
            raise BadLoginError("Password does not match")

    def add_account(self, username, display_name, password, access_level):
        pass

    def remove_account(self, username):
        pass

    def alter_account(self, username, display_name, password, access_level):
        pass
