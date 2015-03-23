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
        self.inputs = {
            #"input1": Gst.ElementFactory.make('autovideosrc', "input1"),
            "input1": Gst.ElementFactory.make('videotestsrc', "input1"),
            "input2": Gst.ElementFactory.make('videotestsrc', "input2"),
            "input3": Gst.ElementFactory.make('videotestsrc', "input3"),
            "input4": Gst.ElementFactory.make('videotestsrc', "input4")
        }
        self.inputs["input2"].set_property("pattern", "ball")
        self.inputs["input3"].set_property("pattern", "ball")
        self.inputs["input4"].set_property("pattern", "ball")

        self.xids = {}

        self.videoscales = {}
        self.tees = {}
        self.vicons = {}
        self.queues = {}
        scaler_caps = Gst.caps_from_string('video/x-raw, width=320, height=180');

        for it in range(1, 2+1):
            self.tees['tee%i' % it] = Gst.ElementFactory.make('tee', 'tee%i' % it)
            self.videoscales['videoscale%i' % it] = Gst.ElementFactory.make('videoconvert', 'videoscale%i' % it)
            self.vicons["vicon%i" % it] = Gst.ElementFactory.make('xvimagesink', "vicon%i" % it)
            self.queues["queue%i" % it] = Gst.ElementFactory.make('queue')

            self.pipeline.add(self.inputs['input%i' % it])
            self.pipeline.add(self.videoscales['videoscale%i' % it])
            self.pipeline.add(self.tees['tee%i' % it])
            self.pipeline.add(self.vicons['vicon%i' % it])
            self.pipeline.add(self.queues['queue%i' % it])

            self.inputs['input%i' % it].link( self.videoscales['videoscale%i' % it] )
            self.videoscales['videoscale%i' % it].link_filtered( self.tees['tee%i' % it], scaler_caps )
            self.tees['tee%i' % it].link(self.queues['queue%i' % it])
            self.queues['queue%i' % it].link(self.vicons['vicon%i' % it])

        pad1 = self.tees["tee1"].get_request_pad('src_1')
        pad2 = self.tees["tee2"].get_request_pad('src_1')

        #self.live_mixer = Gst.ElementFactory.make('glcolorscale', None)
        #self.pipeline.add(self.live_mixer)

        self.live_sink = Gst.ElementFactory.make('xvimagesink', "live_sink")
        self.preview_sink = Gst.ElementFactory.make('xvimagesink', "preview_sink")
        self.live_queue = Gst.ElementFactory.make('queue', None)
        self.preview_queue = Gst.ElementFactory.make('queue', None)

        # Add elements to the pipeline
        self.pipeline.add(self.live_queue, self.preview_queue)
        self.pipeline.add(self.live_sink, self.preview_sink)

        pad1.link(self.preview_queue.get_static_pad("sink"))
        pad2.link(self.live_queue.get_static_pad("sink"))

        self.preview_queue.link(self.preview_sink)
        self.live_queue.link(self.live_sink)

        #gstreamer_link_many(self.src, self.videoscale, self.sink)

        #self.inputs["input2"].link(self.preview_sink)

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
