from subprocess import Popen

def start_streaming() -> Popen:
    cmd = [
        "gst-launch-1.0.exe",
        "d3d11screencapturesrc", "show-cursor=true",
        "!", "videoconvert",
        "!", "x264enc", "tune=zerolatency", "speed-preset=ultrafast", "key-int-max=30", "bitrate=2000",
        "!", "video/x-h264,stream-format=avc,alignment=au",
        "!", "queue",
        "!", "webrtcsink", "name=sink",
        "run-signalling-server=true", "run-web-server=true", "web-server-host-addr=http://0.0.0.0:8080/",
        "wasapisrc", "loopback=true", "low-latency=true",
        "!", "audioconvert",
        "!", "audioresample",
        "!", "opusenc",
        "!", "queue",
        "!", "sink."
    ]
    return Popen(cmd)