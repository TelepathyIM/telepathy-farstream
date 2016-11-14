#!/usr/bin/env python
#
# callchannel.py
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
gi.require_version('Gst', '1.0')
gi.require_version('TelepathyGLib', '0.12')
gi.require_version('TelepathyFarstream', '0.6')
from gi.repository import GLib, GObject, Gst, TelepathyFarstream, Farstream, TelepathyGLib

import sys

Gst.init(sys.argv)

from util import *

class CallChannel:
    def __init__ (self, connection, channel):
        self.conn = connection
        self.channel = channel
        self.tfchannel = None

        channel.connect ("state-changed", self.state_changed_cb)

        self.pipeline = Gst.Pipeline(None)
        self.pipeline.get_bus().add_signal_watch()
        self.pipeline.get_bus().connect ("message", self.async_handler)

        self.notifier = notifier = Farstream.ElementAddedNotifier()
        notifier.set_properties_from_file("element-properties")
        notifier.add(self.pipeline)

        TelepathyFarstream.Channel.new_async (channel, self.tpfs_created)

    def state_changed_cb(self, channel, state, flags, reason, details):
        print "* StateChanged:\n State: %s (%d)\n Flags: %s" % (
            call_state_to_s (state), state, call_flags_to_s (flags))
        print "\tReason: " + reason.message,
        print '\tDetails:'
        for key, value in details.iteritems():
            print "\t  %s: %s" % (key, value)
        else:
            print '\t  None'

        if state == TelepathyGLib.CallState.ENDED:
            self.close()


    def close (self):
        print "Closing the channel"

        # close and cleanup
        self.channel.close_async()

        self.pipeline.set_state (Gst.State.NULL)
        self.pipeline = None

        self.tfchannel = None
        self.notifier = None

    def async_handler (self, bus, message):
        if self.tfchannel != None:
            self.tfchannel.bus_message(message)
        return True

    def tpfs_created (self, source, result):
        tfchannel = self.tfchannel = source.new_finish(source, result)
        tfchannel.connect ("fs-conference-added", self.conference_added)
        tfchannel.connect ("content-added", self.content_added)


    def src_pad_added (self, content, handle, stream, pad, codec):
        type = content.get_property ("media-type")
        if type == Farstream.MediaType.AUDIO:
            sink = Gst.parse_bin_from_description("audioconvert ! audioresample ! audioconvert ! autoaudiosink", True)
        elif type == Farstream.MediaType.VIDEO:
            sink = Gst.parse_bin_from_description("videoconvert ! videoscale ! autovideosink", True)

        self.pipeline.add(sink)
        pad.link(sink.get_static_pad("sink"))
        sink.set_state(Gst.State.PLAYING)

    def get_codec_config (self, media_type):
        if media_type == Farstream.MediaType.VIDEO:
            codecs = [ farstream.Codec.new(farstream.CODEC_ID_ANY, "VP8",
                                           Farstream.MediaType.VIDEO, 0),
                       farstream.Codec.new(farstream.CODEC_ID_ANY, "H264",
                                           Farstream.MediaType.VIDEO, 0) ]
            if self.conn.GetProtocol() == "sip" :
                codecs += [ Farstream.Codec.new(Farstream.CODEC_ID_DISABLE, "THEORA",
                                        Farstream.MediaType.VIDEO, 0) ]
            else:
                codecs += [ Farstream.Codec.new(Farstream.CODEC_ID_ANY, "THEORA",
                                        Farstream.MediaType.VIDEO, 0) ]
            codecs += [
                farstream.Codec.new.new(Farstream.CODEC_ID_ANY, "H263",
                                        Farstream.MediaType.VIDEO, 0),
                farstream.Codec.new(Farstream.CODEC_ID_DISABLE, "DV",
                                    Farstream.MediaType.VIDEO, 0),
                farstream.Codec.new(Farstream.CODEC_ID_ANY, "JPEG",
                                    Farstream.MediaType.VIDEO, 0),
                farstream.Codec.new(Farstream.CODEC_ID_ANY, "MPV",
                                    Farstream.MediaType.VIDEO, 0),
            ]

        else:
            codecs = [
                Farstream.Codec.new(Farstream.CODEC_ID_ANY, "OPUS",
                                    Farstream.MediaType.AUDIO, 0 ),
                Farstream.Codec.new(Farstream.CODEC_ID_ANY, "SPEEX",
                                    Farstream.MediaType.AUDIO, 16000 ),
                Farstream.Codec.new(Farstream.CODEC_ID_ANY, "SPEEX",
                                    Farstream.MediaType.AUDIO, 8000 ),
                Farstream.Codec.new(Farstream.CODEC_ID_DISABLE, "G722",
                                    Farstream.MediaType.AUDIO, 0 ),
                Farstream.Codec.new(Farstream.CODEC_ID_DISABLE, "G726-16",
                                    Farstream.MediaType.AUDIO, 0 ),
                Farstream.Codec.new(Farstream.CODEC_ID_DISABLE, "L16",
                                    Farstream.MediaType.AUDIO, 0 ),
                Farstream.Codec.new(Farstream.CODEC_ID_DISABLE, "AMR",
                                    Farstream.MediaType.AUDIO, 0 ),
                Farstream.Codec.new(Farstream.CODEC_ID_DISABLE, "SIREN",
                                    Farstream.MediaType.AUDIO, 0 ),
                Farstream.Codec.new(Farstream.CODEC_ID_DISABLE, "MPA",
                                    Farstream.MediaType.AUDIO, 0 ),
                Farstream.Codec.new(Farstream.CODEC_ID_DISABLE, "MPA-ROBUST",
                                    Farstream.MediaType.AUDIO, 0 ),
                Farstream.Codec.new(Farstream.CODEC_ID_DISABLE,
                                    "X-MP3-DRAFT-00",
                                    Farstream.MediaType.AUDIO, 0 )
            ]
        return codecs

    def content_added(self, channel, content):
        sinkpad = content.get_property ("sink-pad")

        mtype = content.get_property ("media-type")
        prefs = self.get_codec_config (mtype)
        if prefs != None:
            try:
                content.props.fs_session.set_codec_preferences(prefs)
            except GLib.GError, e:
                print e.message

        content.connect ("src-pad-added", self.src_pad_added)

        if mtype == Farstream.MediaType.AUDIO:
            src = Gst.parse_bin_from_description("audiotestsrc is-live=1", True)
        elif mtype == Farstream.MediaType.VIDEO:
            src = Gst.parse_bin_from_description("videotestsrc is-live=1 ! " \
                "capsfilter caps=video/x-raw-yuv,width=320,height=240", True)

        self.pipeline.add(src)
        src.get_static_pad("src").link(sinkpad)
        src.set_state(Gst.State.PLAYING)

    def conference_added (self, channel, conference):
        self.pipeline.add(conference)
        self.pipeline.set_state(Gst.State.PLAYING)

