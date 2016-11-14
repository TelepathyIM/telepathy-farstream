# callhandler.py
# Copyright (C) 2008-2010 Collabora Ltd.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import gi
gi.require_version('TelepathyGLib', '0.12')
from gi.repository import GObject, Gio, TelepathyGLib

from constants import *

from callchannel import CallChannel

class CallHandler:
    def __init__(self, bus_name = 'CallDemo'):
        TelepathyGLib.debug_set_flags("all")
        am = TelepathyGLib.AccountManager.dup()
        self.handler = handler = TelepathyGLib.SimpleHandler.new_with_am(
            am, True, False, bus_name, True, self.handle_channels_cb)

        handler.add_handler_filter({
            TelepathyGLib.PROP_CHANNEL_CHANNEL_TYPE: TelepathyGLib.IFACE_CHANNEL_TYPE_CALL,

            TelepathyGLib.PROP_CHANNEL_TARGET_HANDLE_TYPE: int(TelepathyGLib.HandleType.CONTACT)
        })
        self.bus_name = handler.get_bus_name()

        handler.register()

    def handle_channels_cb (self, handler, account, conn, channels,
                            requests_satisfied, user_action_time, context):
        assert len(channels) == 1
        cchannel = CallChannel(conn, channels[0])
        context.accept()
        channels[0].accept_async(None)

if __name__ == '__main__':
    GObject.threads_init()
    loop = GObject.MainLoop()
    CallHandler()
    loop.run()
