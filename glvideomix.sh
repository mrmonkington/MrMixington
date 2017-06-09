read -r -d '' CMD <<- EOM

	glvideomixer name=mix sink_0::alpha=0.7 sink_1::alpha=0.5 !
		video/x-raw(memory:GLMemory),width=1920,height=1080 !
		glcolorscale !
		video/x-raw(memory:GLMemory),width=960,height=540 !
		glsinkbin sink=gtkglsink

	gltestsrc is-live=true pattern=0
		! video/x-raw(memory:GLMemory),framerate=60/1,width=1920,height=1080
		! mix.sink_0

	gltestsrc is-live=true pattern=13
		! video/x-raw(memory:GLMemory),framerate=60/1,width=1920,height=1080
		! mix.sink_1
EOM

gst-launch-1.0 $CMD
