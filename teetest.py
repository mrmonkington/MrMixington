#!/usr/bin/python3

import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst, Gtk

# Needed for window.get_xid(), xvimagesink.set_window_handle(), respectively:
from gi.repository import GdkX11, GstVideo

#import ctypes
#import sys
#if sys.platform.startswith('linux'):
#    x11 = ctypes.cdll.LoadLibrary('libX11.so')
#    x11.XInitThreads()

GObject.threads_init()
Gst.init(None)

def gstreamer_link_many(*args):
    for i in range(0, len(args)-1):
        args[i].link(args[i+1])

class Webcam:
    def __init__(self):
        self.builder = Gtk.Builder()
        self.builder.add_from_file("main.ui")
        self.window = self.builder.get_object("window1")
        self.window.connect('destroy', self.quit)
        self.window.set_default_size(960, 540)

        self.live_screen = self.builder.get_object("live_screen")
        self.preview_screen = self.builder.get_object("preview_screen")

        # Create GStreamer pipeline
        self.pipeline = Gst.Pipeline()

        # Create bus to get events from GStreamer pipeline
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message::error', self.on_error)

        # This is needed to make the video output in our DrawingArea:
        self.bus.enable_sync_message_emission()
        self.bus.connect('sync-message::element', self.on_sync_message)

        # Create GStreamer elements
        self.input = Gst.ElementFactory.make('videotestsrc')
        self.input.set_property("pattern", "ball")

        self.xids = {}

        live_caps = Gst.caps_from_string('video/x-raw, width=960, height=540');
        preview_caps = Gst.caps_from_string('video/x-raw, width=160, height=90');

        self.tee = Gst.ElementFactory.make('tee')
        self.videoscale = Gst.ElementFactory.make('videoconvert')
        self.videoscale_vicon = Gst.ElementFactory.make('videoconvert')
        self.vicon = Gst.ElementFactory.make('xvimagesink', 'vicon1')
        self.queue = Gst.ElementFactory.make('queue')

        self.pipeline.add(self.input)
        self.pipeline.add(self.videoscale)
        self.pipeline.add(self.videoscale_vicon)
        self.pipeline.add(self.tee)
        self.pipeline.add(self.queue)
        self.pipeline.add(self.vicon)

        self.input.link( self.tee )
        #self.input.link_filtered( self.tee, live_caps )
        #self.input.link( self.videoscale )
        #self.videoscale.link_filtered( self.tee, scaler_caps )
        self.tee.link(self.queue)
        #self.queue.link(self.videoscale_vicon)
        #self.videoscale_vicon.link_filtered( self.vicon, preview_caps )
        self.queue.link( self.vicon )

        self.live_queue = Gst.ElementFactory.make('queue', None)
        self.live_sink = Gst.ElementFactory.make('xvimagesink', "live_sink")

        self.pipeline.add(self.live_queue)
        self.pipeline.add(self.live_sink)

        self.tee.link_pads_filtered('src_1', self.live_queue, "sink", live_caps)

        self.live_queue.link(self.live_sink)

    def run(self):
        self.window.show_all()
        # You need to get the XID after window.show_all().  You shouldn't get it
        # in the on_sync_message() handler because threading issues will cause
        # segfaults there.
        self.live_xid = self.live_screen.get_property('window').get_xid()
        self.preview_xid = self.preview_screen.get_property('window').get_xid()
        for it in range(1, 4+1):
            print('get xid for vicon%i' % it)
            self.xids["vicon%i" % it] = self.builder.get_object("vicon%i" % it).get_property('window').get_xid()

        self.pipeline.set_state(Gst.State.PLAYING)
        Gtk.main()

    def quit(self, window):
        self.pipeline.set_state(Gst.State.NULL)
        Gtk.main_quit()

    def on_sync_message(self, bus, msg):
        if msg.get_structure().get_name() == 'prepare-window-handle':
            if msg.src.name == "live_sink":
                print('live prepare-window-handle')
                msg.src.set_property('force-aspect-ratio', True)
                msg.src.set_window_handle(self.live_xid)
            if msg.src.name == "preview_sink":
                print('preview prepare-window-handle')
                msg.src.set_property('force-aspect-ratio', True)
                msg.src.set_window_handle(self.preview_xid)
            if msg.src.name.startswith("vicon"):
                print('"%s" prepare-window-handle' % msg.src.name)
                msg.src.set_property('force-aspect-ratio', True)
                msg.src.set_window_handle(self.xids[msg.src.name])
                

    def on_error(self, bus, msg):
        print('on_error():', msg.parse_error())


webcam = Webcam()
webcam.run()
