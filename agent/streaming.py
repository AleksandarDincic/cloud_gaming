from subprocess import Popen

def start_audio_streaming() -> Popen:
    cmd = [
        "gst-launch-1.0.exe",
        "wasapisrc", "loopback=true", "low-latency=true",
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

    # GST_TRACERS = "latency(flags=pipeline)"
    # GST_DEBUG_FILE = ".\latency.log"
    # $env:GST_DEBUG = "GST_TRACER:7"

    cmd = [
        "gst-launch-1.0.exe",
        "d3d12screencapturesrc", "show-cursor=true", f"window-handle={window_handle}",
        "!", "nvh264enc", "tune=ultra-low-latency", "preset=p1", "rc-mode=cbr", "bitrate=4000", "bframes=0", "rc-lookahead=0", "gop-size=30", "zerolatency=true", "vbv-buffer-size=400", "repeat-sequence-header=true", "qp-min=25", "qp-max=35",
        "!", "video/x-h264,stream-format=avc,alignment=au",
        "!", "queue", "max-size-buffers=1", "max-size-time=0", "max-size-bytes=0", "leaky=downstream",
        "!", "webrtcsink",
        "run-signalling-server=true"
    ]
    return Popen(cmd)