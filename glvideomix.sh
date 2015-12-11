gst-launch-1.0 \
	videotestsrc pattern=1 ! \
	video/x-raw,format=AYUV,framerate=\(fraction\)30/1,width=100,height=100 ! \
	glvideomixer name=mix sink_0::alpha=0.7 sink_1::alpha=0.5 ! \
	glimagesink \
	videotestsrc ! \
	video/x-raw,format=AYUV,framerate=\(fraction\)30/1,width=320,height=240 ! mix.sink_1
