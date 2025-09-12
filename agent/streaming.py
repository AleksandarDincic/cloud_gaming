from subprocess import Popen

def start_audio_streaming() -> Popen:
    cmd = [
        "gst-launch-1.0.exe",
        "wasapisrc", "loopback=true", "low-latency=true",
        "!", "audioconvert",
        "!", "audioconvert",
        "!", "audioresample",
        "!", "audio/x-raw,rate=48000,channels=2,format=S16LE",
        "!", "opusenc", "bitrate=96000",
        "!", "queue", "max-size-buffers=1", "max-size-time=0", "max-size-bytes=0", "leaky=downstream",
        "!", "webrtcsink",
        "run-signalling-server=true", "signalling-server-port=8444"
    ]
    return Popen(cmd)

def start_video_streaming(window_handle: int) -> Popen:
    # cmd = [
    #     "gst-launch-1.0.exe",
    #     "d3d11screencapturesrc", "show-cursor=true",
    #     "!", "videoconvert",
    #     #"!", "x264enc", "tune=zerolatency", "speed-preset=ultrafast", "key-int-max=30", "bitrate=2000",
    #     "!", "nvh264enc", "tune=ultra-low-latency", "preset=p1",
    #     "!", "video/x-h264,stream-format=avc,alignment=au",
    #     "!", "queue",
    #     "!", "webrtcsink", "name=sink",
    #     "run-signalling-server=true", "run-web-server=true", "web-server-host-addr=http://0.0.0.0:8080/",
    #     "wasapisrc", "loopback=true", "low-latency=true",
    #     "!", "audioconvert",
    #     "!", "audioresample",
    #     "!", "opusenc",
    #     "!", "queue",
    #     "!", "sink."
    # ]

    # Full pipeline with audio and video
    # cmd = [
    #      "gst-launch-1.0.exe",
    #      "d3d11screencapturesrc", "show-cursor=true", f"window-handle={window_handle}",
    #      "!", "videoconvert",
    #      "!", "video/x-raw,format=NV12,framerate=60/1",
    #      "!", "nvh264enc", "tune=ultra-low-latency", "preset=p4", "rc-mode=cbr", "bitrate=4000", "gop-size=30", "zerolatency=true", "vbv-buffer-size=8000", "aud=false", "qp-min=18", "qp-max=28",
    #      "!", "video/x-h264,stream-format=avc,alignment=au",
    #      "!", "queue", "max-size-buffers=2", "max-size-time=100000000", "max-size-bytes=0", "leaky=upstream",
    #      "!", "webrtcsink", "name=sink",
    #      "run-signalling-server=true", "run-web-server=true", "web-server-host-addr=http://0.0.0.0:8080/",
    #      "wasapisrc", "loopback=true", "low-latency=true",
    #      "!", "audioconvert",
    #      "!", "audioresample",
    #      "!", "audio/x-raw,rate=48000,channels=2,format=S16LE",
    #      "!", "opusenc", "bitrate=128000", "inband-fec=false", "dtx=false",
    #      "!", "queue", "max-size-buffers=2", "max-size-time=100000000", "max-size-bytes=0", "leaky=upstream",
    #      "!", "sink."
    # ]

    # Video-only pipeline (balanced quality)
    # cmd = [
    #     "gst-launch-1.0.exe",
    #     "d3d11screencapturesrc", "show-cursor=true", f"window-handle={window_handle}",
    #     "!", "videoconvert",
    #     "!", "video/x-raw,format=NV12,framerate=60/1",
    #     "!", "nvh264enc", "tune=ultra-low-latency", "preset=p4", "rc-mode=cbr", "bitrate=4000", "gop-size=30", "zerolatency=true", "vbv-buffer-size=8000", "aud=false", "qp-min=18", "qp-max=28",
    #     "!", "video/x-h264,stream-format=avc,alignment=au",
    #     "!", "queue", "max-size-buffers=2", "max-size-time=100000000", "max-size-bytes=0", "leaky=upstream",
    #     "!", "webrtcsink", "name=sink",
    #     "run-signalling-server=true", "run-web-server=true", "web-server-host-addr=http://0.0.0.0:8080/"
    # ]

    cmd = [
        "gst-launch-1.0.exe",
        "d3d11screencapturesrc", "show-cursor=true", f"window-handle={window_handle}",
        "!", "videoconvert",
        "!", "video/x-raw,format=NV12,framerate=60/1",
        "!", "nvh264enc", "tune=ultra-low-latency", "preset=p1", "rc-mode=cbr", "bitrate=1000", "gop-size=1", "zerolatency=true", "vbv-buffer-size=1000", "aud=false", "qp-min=25", "qp-max=35",
        "!", "video/x-h264,stream-format=avc,alignment=au",
        "!", "queue", "max-size-buffers=0", "max-size-time=0", "max-size-bytes=0", "leaky=upstream",
        "!", "webrtcsink", "name=sink",
        "run-signalling-server=true", "run-web-server=true", "web-server-host-addr=http://0.0.0.0:8080/"
    ]
    return Popen(cmd)