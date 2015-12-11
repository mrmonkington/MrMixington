# GST pipelines commands that work :)

## VAAPI stuff

VAAPI accelerated render and scale (~30% CPU)

```
gst-launch-1.0 videotestsrc ! video/x-raw,framerate=30000/1001,width=1920,height=1080,format=I420 ! vaapipostproc width=320 ! tee name=t ! queue ! vaapisink t. ! queue ! vaapisink
```

VAAPI accel encode (2 x 1080p30 8000Mbit = ~50% CPU)

```
gst-launch-1.0 videotestsrc is-live=true num-buffers=250 ! video/x-raw,framerate=30000/1001,width=1920,height=1080,format=I420 ! tee name=t ! vaapiencode_h264 bitrate=8000 ! mp4mux ! filesink location=monk.mp4 t. ! vaapiencode_h264 bitrate=8000 ! mp4mux ! filesink location=monk_2.mp4
```

