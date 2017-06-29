#!/usr/bin/python3

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import GObject, Gst, Gtk, Gdk

# Needed for window.get_xid(), xvimagesink.set_window_handle(), respectively:
from gi.repository import GdkX11, GstVideo

#import ctypes
#x11 = ctypes.cdll.LoadLibrary('libX11.so')
#x11.XInitThreads()

#import ctypes
#import sys
#if sys.platform.startswith('linux'):
#    x11 = ctypes.cdll.LoadLibrary('libX11.so')
#    x11.XInitThreads()

MASTER_WIDTH=1920
MASTER_HEIGHT=1080
FPS=60
#MASTER_WIDTH=960
#MASTER_HEIGHT=540

GObject.threads_init()
Gst.init(None)
Gtk.init(None)

def gstreamer_link_many(*args):
    for i in range(0, len(args)-1):
        args[i].link(args[i+1])

class Mixington:
    def __init__(self):
        self.builder = Gtk.Builder()
        self.builder.add_from_file("main.ui")
        self.window = self.builder.get_object("window1")
        self.window.connect('destroy', self.quit)
        self.window.connect('key-press-event', self.keypress)
        self.window.set_default_size(MASTER_WIDTH, MASTER_HEIGHT)

        self.live_screen = self.builder.get_object("live_screen")
        self.preview_screen = self.builder.get_object("preview_screen")
        self.vicon_screen = {}
        for it in range(1, 4+1):
            self.vicon_screen[it] = self.builder.get_object("vicon%i" % it)
            self.builder.get_object("switch%i" % it).connect("clicked", self.clicked, it-1)
        self.xids = {}

    def init_pipeline(self):
        # Create GStreamer pipeline
        self.pipeline = Gst.Pipeline()

        # Create bus to get events from GStreamer pipeline
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message::error', self.on_error)

        # This is needed to make the video output in our DrawingArea:
        self.bus.enable_sync_message_emission()
        self.bus.connect('sync-message::element', self.on_sync_message)

        #Gst.ElementFactory.make('videotestsrc', "input1"), Create GStreamer elements
        self.inputs = {}

        self.videoscales = {}
        self.videoscales_vicon = {}
        self.tees = {}
        self.vicons = {}
        self.queues = {}
        self.sinks = {}
        src_caps = Gst.caps_from_string('video/x-raw(memory:GLMemory), width=%i, height=%i, framerate=%i/1' % (MASTER_WIDTH, MASTER_HEIGHT, FPS));
        scaler_caps = Gst.caps_from_string('video/x-raw(memory:GLMemory), width=%i, height=%i' % (MASTER_WIDTH, MASTER_HEIGHT));
        preview_caps = Gst.caps_from_string('video/x-raw(memory:GLMemory), width=160, height=90');

        for it in range(1, 4+1):
            self.inputs["input%i" % it] = Gst.ElementFactory.make('gltestsrc', "input%i" % it);
            self.inputs["input%i" % it].set_property("is-live", "true")
            #self.inputs["input%i" % it].set_property("pattern", "circular")
            self.tees['tee%i' % it] = Gst.ElementFactory.make('tee', 'tee%i' % it)
            #self.videoscales['videoscale%i' % it] = Gst.ElementFactory.make('videoconvert', 'videoscale%i' % it)
            self.videoscales_vicon['videoscale%i' % it] = Gst.ElementFactory.make('glcolorscale', 'videoscalevicon%i' % it)
            self.queues["queue%i" % it] = Gst.ElementFactory.make('queue')

            self.vicons["vicon%i" % it] = Gst.ElementFactory.make('glsinkbin', "vicon%i" % it)
            self.sinks[it] = Gst.ElementFactory.make('gtkglsink')
            self.vicons["vicon%i" % it].set_property('sink', self.sinks[it])
            self.builder.get_object('vicon%i' % it).add_overlay(
                self.sinks[it].get_property('widget'))
            #self.window.add(self.sinks[it].get_property('widget'))

            self.pipeline.add(self.inputs['input%i' % it])
            #self.pipeline.add(self.videoscales['videoscale%i' % it])
            self.pipeline.add(self.videoscales_vicon['videoscale%i' % it])
            self.pipeline.add(self.tees['tee%i' % it])
            self.pipeline.add(self.vicons['vicon%i' % it])
            self.pipeline.add(self.queues['queue%i' % it])

            self.inputs['input%i' % it].link_filtered( self.tees['tee%i' % it], src_caps )
            #self.inputs['input%i' % it].link_filtered( self.tees['tee%i' % it], scaler_caps )

            #self.inputs['input%i' % it].link( self.videoscales['videoscale%i' % it] )

            #self.videoscales['videoscale%i' % it].link_filtered( self.tees['tee%i' % it], scaler_caps )
            self.tees['tee%i' % it].link(self.queues['queue%i' % it])
            self.queues['queue%i' % it].link(self.videoscales_vicon['videoscale%i' % it])
            self.videoscales_vicon['videoscale%i' % it].link_filtered( self.vicons['vicon%i' % it], scaler_caps )
            #self.queues['queue%i' % it].link( self.vicons['vicon%i' % it] )

        self.inputs["input1"].set_property("pattern", "checkers-8")
        self.inputs["input3"].set_property("pattern", "checkers-8")

        #pad1 = self.tees["tee1"].get_request_pad('src_1')
        #pad2 = self.tees["tee2"].get_request_pad('src_1')
        #pad3 = self.tees["tee2"].get_request_pad('src_2')

        self.live_queue = Gst.ElementFactory.make('queue', None)
        self.pipeline.add(self.live_queue)
        self.live_queue_2 = Gst.ElementFactory.make('queue', None)
        self.pipeline.add(self.live_queue_2)
        self.live_queue_3 = Gst.ElementFactory.make('queue', None)
        self.pipeline.add(self.live_queue_3)
        self.live_queue_4 = Gst.ElementFactory.make('queue', None)
        self.pipeline.add(self.live_queue_4)

        self.preview_queue = Gst.ElementFactory.make('queue', None)
        self.pipeline.add(self.preview_queue)

        self.preview_mixer = Gst.ElementFactory.make('glvideomixer', None)
        self.pipeline.add(self.preview_mixer)

        self.live_mixer = Gst.ElementFactory.make('glvideomixer', None)
        self.pipeline.add(self.live_mixer)

        self.live_sink = Gst.ElementFactory.make('glsinkbin', "live_sink")
        self.live_gtk_sink = Gst.ElementFactory.make('gtkglsink')
        self.live_sink.set_property('sink', self.live_gtk_sink)
        self.pipeline.add(self.live_sink)
        #self.window.add(self.live_gtk_sink.get_property('widget'))
        self.builder.get_object('live_screen').add_overlay(
            self.live_gtk_sink.get_property('widget'))

        self.preview_sink = Gst.ElementFactory.make('glsinkbin', "preview_sink")
        self.preview_gtk_sink = Gst.ElementFactory.make('gtkglsink')
        self.preview_sink.set_property('sink', self.preview_gtk_sink)
        self.pipeline.add(self.preview_sink)
        #self.window.add(self.preview_gtk_sink.get_property('widget'))
        self.builder.get_object('preview_screen').add_overlay(
            self.preview_gtk_sink.get_property('widget'))

        # Add elements to the pipeline

        self.tees["tee2"].link_pads('src_2', self.preview_queue, "sink")

        self.tees["tee1"].link_pads('src_1', self.live_queue, "sink")
        self.tees["tee2"].link_pads('src_1', self.live_queue_2, "sink")
        self.tees["tee3"].link_pads('src_1', self.live_queue_3, "sink")
        self.tees["tee4"].link_pads('src_1', self.live_queue_4, "sink")

        self.live_queue.link(self.live_mixer)
        self.live_queue_2.link(self.live_mixer)
        self.live_queue_3.link(self.live_mixer)
        self.live_queue_4.link(self.live_mixer)

        mix_pad_1 = self.live_mixer.sinkpads[0]
        mix_pad_2 = self.live_mixer.sinkpads[1]
        mix_pad_3 = self.live_mixer.sinkpads[2]
        mix_pad_4 = self.live_mixer.sinkpads[3]

        mix_pad_1.set_property( "alpha", 1.0 )
        mix_pad_2.set_property( "alpha", 0.0 )
        mix_pad_3.set_property( "alpha", 0.0 )
        mix_pad_4.set_property( "alpha", 0.0 )

        self.preview_queue.link(self.preview_mixer)
        self.preview_mixer.link(self.preview_sink)
        self.live_mixer.link(self.live_sink)

        #gstreamer_link_many(self.src, self.videoscale, self.sink)

        #self.inputs["input2"].link(self.preview_sink)

    def clicked(self, widget, *data):
        [num,] = data
        print num
        for a in range(0,4):
            if a == num:
                self.live_mixer.sinkpads[a].set_property('alpha', 1.0)
            else:
                self.live_mixer.sinkpads[a].set_property('alpha', 0.0)

    def keypress(self, win, event):
        if event.keyval == Gdk.KEY_F11:
            win.is_fullscreen = not getattr(win, 'is_fullscreen', False)
            action = win.fullscreen if win.is_fullscreen else win.unfullscreen
            action()
            self.builder.get_object('statusbar1').set_visible(not win.is_fullscreen)

    def init(self):
        self.window.show_all()
        # You need to get the XID after window.show_all().  You shouldn't get it
        # in the on_sync_message() handler because threading issues will cause
        # segfaults there.

        #self.live_xid = self.live_screen.get_property('window').get_xid()
        #self.preview_xid = self.preview_screen.get_property('window').get_xid()
        #for it in range(1, 4+1):
        #    self.xids["vicon%i" % it] = self.vicon_screen[it].get_property('window').get_xid()

    def run(self):
        self.pipeline.set_state(Gst.State.PLAYING)
        print( "run" )
        Gtk.main()

    def quit(self, window):
        self.pipeline.set_state(Gst.State.NULL)
        Gtk.main_quit()

    def on_sync_message(self, bus, msg):
        #if msg.get_structure().get_name() == 'prepare-window-handle':
        #    print(msg.src.name);
        #    if msg.src.name == "live_sink":
        #        print('live prepare-window-handle')
        #        msg.src.set_property('force-aspect-ratio', True)
        #        msg.src.set_window_handle(self.live_xid)
        #    if msg.src.name == "preview_sink":
        #        print('preview prepare-window-handle')
        #        msg.src.set_property('force-aspect-ratio', True)
        #        msg.src.set_window_handle(self.preview_xid)
        #    if msg.src.name.startswith("vicon"):
        #        print('"%s" prepare-window-handle' % msg.src.name)
        #        msg.src.set_property('force-aspect-ratio', True)
        #        msg.src.set_window_handle(self.xids[msg.src.name])
        pass
                

    def on_error(self, bus, msg):
        print('on_error():', msg.parse_error())


mixer = Mixington()
mixer.init_pipeline()
mixer.init()
mixer.run()
