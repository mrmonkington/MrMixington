gst-launch-1.0 \
	videotestsrc pattern=1 ! \
	video/x-raw,format=AYUV,framerate=\(fraction\)10/1,width=100,height=100 ! \
	videobox border-alpha=0 top=-70 bottom=-70 right=-220 ! \
	videomixer name=mix sink_0::alpha=0.7 sink_1::alpha=0.5 ! \
	videoconvert ! xvimagesink \
	videotestsrc ! \
	video/x-raw,format=AYUV,framerate=\(fraction\)5/1,width=320,height=240 ! mix.sink_1
