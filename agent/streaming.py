from subprocess import Popen

def start_streaming(window_handle: int, audio_device: str) -> Popen:
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

    cmd = [
        "gst-launch-1.0.exe",
        "d3d11screencapturesrc", "show-cursor=true", f"window-handle={window_handle}",
        "!", "videoconvert",
        "!", "video/x-raw,format=NV12",
        "!", "nvh264enc", "tune=ultra-low-latency", "preset=p1", "rc-mode=cbr", "bitrate=2000", "gop-size=15", "zerolatency=true",
        "!", "video/x-h264,stream-format=avc,alignment=au",
        "!", "queue", "max-size-buffers=1", "max-size-time=0", "max-size-bytes=0", "leaky=downstream",
        "!", "webrtcsink", "name=sink",
        "run-signalling-server=true", "run-web-server=true", "web-server-host-addr=http://0.0.0.0:8080/",
        "wasapisrc", "loopback=true", "low-latency=true", #f"device={audio_device}"
        "!", "audioconvert",
        "!", "audioresample",
        "!", "audio/x-raw,rate=48000,channels=2,format=S16LE",
        "!", "opusenc", "bitrate=96000",
        "!", "queue", "max-size-buffers=1", "max-size-time=0", "max-size-bytes=0", "leaky=downstream",
        "!", "sink."
    ]
    return Popen(cmd)