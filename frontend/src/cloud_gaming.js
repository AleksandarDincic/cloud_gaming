let videoElement = null;
let audioElement = null;
let ws = null;

let keys_bit_mask = new Uint8Array(32);
let mouse_buttons = 0;
let mouse_dx = 0, mouse_dy = 0;
let mouse_wheel = 0;

let previous_input_keys = new Uint8Array(32);
let previous_mouse_buttons = 0;

let input_packet = new Uint8Array(56); // 32 bytes for keys + 16 bytes for mouse data + 8 bytes for timestamp


function setKey(vk, down) {
  const b = vk >>> 3, bit = vk & 7;
  if (b < 32) {
    if (down) keys_bit_mask[b] |=  (1<<bit);
    else      keys_bit_mask[b] &= ~(1<<bit);
  }
};

function stateChanged() {
  for (let i = 0; i < 32; i++) {
    if (keys_bit_mask[i] !== previous_input_keys[i]) return true;
  }
  return (mouse_buttons !== previous_mouse_buttons || 
          mouse_dx !== 0 || 
          mouse_dy !== 0 || 
          mouse_wheel !== 0);
}

function sendInputPacket(force) {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        console.log("Websocket not open, not sending")
        return;
    }

    if (!force) {
        if (document.pointerLockElement !== videoElement)  {
            console.log("Pointer lock not on video, not sending")
            return;
        }

        if (!stateChanged()) {
            console.log("State hasnt changed, not sending")
            return;
        }
    }

    // Packet contains:
    // Keyboard [0-31]
    // Mouse [32-47]
        // Mouse buttons [32-35]
        // Mouse movement [36-43]
        // Mouse wheel [44-47]
    // Timestamp [48-55]

    input_packet.set(keys_bit_mask, 0);
    
    let view = new DataView(input_packet.buffer);
    view.setUint32(32, mouse_buttons, true);
    view.setInt32(36, mouse_dx, true);
    view.setInt32(40, mouse_dy, true);
    view.setInt32(44, mouse_wheel, true);

    let timestamp = Date.now();
    view.setBigUint64(48, BigInt(timestamp), true);

    ws.send(input_packet);

    previous_input_keys.set(keys_bit_mask);
    previous_mouse_buttons = mouse_buttons;
    
    mouse_dx = 0;
    mouse_dy = 0;
    mouse_wheel = 0;
}


function showError(message) {
    if (message === "" || message === null) {
        document.getElementById("error").style.display = "none";
        document.getElementById("error").textContent = "";
        document.getElementById("stream_player").style.display = "block";
    } else {
        document.getElementById("error").textContent = message;
        document.getElementById("error").style.display = "block";
        document.getElementById("stream_player").style.display = "none";
    }
}

function terminateSession() {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close();
        ws = null;
    }
    
    if (videoElement) {
        videoElement.pause();
        videoElement.srcObject = null;
    }
    
    if (audioElement) {
        audioElement.pause();
        audioElement.srcObject = null;
    }

    showError("Session closed");
}


async function createSession(backend_endpoint) {
    let timeoutToken = new AbortController();
    let timeoutId = setTimeout(() => timeoutToken.abort(), 60000);

    let response;
    try {
        response = await fetch(backend_endpoint, {
            method: "GET",
            signal: timeoutToken.signal
        });
    } finally {
        clearTimeout(timeoutId);
    }

    if (!response) {
        throw new Error("No response from server");
    }

    if (!response.ok) {
        throw new Error(`Failed to create session: ${response.statusText}, ${await response.text()}`);
    }
    let session = await response.json();
    return session;
}

async function init_stream(video_webrtc_config, audio_webrtc_config) {
    videoElement = document.getElementById("stream_player")
    audioElement = document.getElementById("audio_player");

    let videoSession = null;
    let audioSession = null;

    let video_webrtc_api = new GstWebRTCAPI(video_webrtc_config)
    
    let audio_webrtc_api = new GstWebRTCAPI(audio_webrtc_config);

    const videoListener = {
        producerAdded: function (producer) {
            const producerId = producer.id

            console.log(`Adding video producer ${producerId}`);

            if (videoSession) {
                console.log("New video producer was added but session is already running");
                return;
            }

            videoSession = video_webrtc_api.createConsumerSession(producerId);

            videoSession.addEventListener("error", (event) => {
                console.error("Video session error:", event.message, event.error);
            });

            videoSession.addEventListener("closed", () => {
                videoElement.pause();
                videoElement.srcObject = null;
                videoSession = null;
                console.log("Video session closed");
                terminateSession();
            });

            videoSession.addEventListener("streamsChanged", () => {
                const streams = videoSession.streams;
                if (streams.length > 0) {
                    videoElement.srcObject = streams[0];
                    showError("");
                    videoElement.play().catch(err => {
                        showError("Video autoplay error: " + err.message);
                    });
                }
            });

            videoSession.connect();
        },

        producerRemoved: function (producer) {
            console.log("Video producer removed");
            if (videoSession) {
                videoElement.pause();
                videoElement.srcObject = null;
                videoSession = null;
            }
            terminateSession();
        }
    };

    const audioListener = {
        producerAdded: function (producer) {
            const producerId = producer.id

            console.log(`Adding audio producer ${producerId}`);

            if (audioSession) {
                console.log("New audio producer was added but session is already running");
                return;
            }

            audioSession = audio_webrtc_api.createConsumerSession(producerId);

            audioSession.addEventListener("error", (event) => {
                console.error("Audio session error:", event.message, event.error);
            });

            audioSession.addEventListener("closed", () => {
                audioElement.pause();
                audioElement.srcObject = null;
                audioSession = null;
                console.log("Audio session closed");
            });

            audioSession.addEventListener("streamsChanged", () => {
                const streams = audioSession.streams;
                if (streams.length > 0) {
                    audioElement.srcObject = streams[0];
                    audioElement.play().catch(err => {
                        console.error("Audio autoplay error:", err.message);
                    });
                }
            });

            audioSession.connect();
        },

        producerRemoved: function (producer) {
            console.log("Audio producer removed");
            if (audioSession) {
                audioElement.pause();
                audioElement.srcObject = null;
                audioSession = null;
            }
        }
    };

    video_webrtc_api.registerPeerListener(videoListener);
    for (const producer of video_webrtc_api.getAvailableProducers()) {
        videoListener.producerAdded(producer);
    }

    audio_webrtc_api.registerPeerListener(audioListener);
    for (const producer of audio_webrtc_api.getAvailableProducers()) {
        audioListener.producerAdded(producer);
    }

    videoElement.requestPointerLock();

    videoElement.addEventListener("click", () => {
        videoElement.requestPointerLock();
    })

    setInterval(() => {
        sendInputPacket(false);
    }, 1000 / 60);

    addEventListener("keydown", e => setKey(e.keyCode, true),  {passive:true});
    addEventListener("keyup",   e => setKey(e.keyCode, false), {passive:true});

    addEventListener("mousemove", e => {
        if (document.pointerLockElement === videoElement) {
            console.log(`JS: Mouse move - movementX=${e.movementX}, movementY=${e.movementY}`);
            mouse_dx += e.movementX;
            mouse_dy += e.movementY;
            console.log(`JS: Accumulated - dx=${mouse_dx}, dy=${mouse_dy}`);
        }
    }, {passive:true});

    addEventListener("mousedown", e => {
        if (document.pointerLockElement === videoElement) {
            mouse_buttons |= (1 << e.button);
            e.preventDefault();
        }
    });

    addEventListener("mouseup", e => {
        if (document.pointerLockElement === videoElement) {
            mouse_buttons &= ~(1 << e.button);
            e.preventDefault();
        }
    });

    addEventListener("wheel", e => {
        if (document.pointerLockElement === videoElement) {
            mouse_wheel += Math.sign(e.deltaY);
            e.preventDefault();
        }
    });

    document.addEventListener("pointerlockchange", () => {
        if (document.pointerLockElement === null) {
            setKey(27, true);  // Send ESC key
            sendInputPacket(true);
        }
    });
}

const backend_endpoint = `http://localhost:3001`;

async function init() {
    let params = window.location.pathname.split('/');
    let user_name = params[1];
    let game_name = params[2];

    showError("Requesting session...");

    let session_info = null;
    try {
        session_info = await createSession(`${backend_endpoint}/create_session?user=${user_name}&game=${game_name}`);
    }
    catch (e) {
        showError(`Failed to create session: ${e.message}`);
        return;
    }

    console.log("Session info:", session_info);

    let ws_endpoint = session_info.ws_endpoint;
    let video_signalling_endpoint = session_info.video_signalling_endpoint;
    let audio_signalling_endpoint = session_info.audio_signalling_endpoint;

    console.log(`Cloud gaming input: ${user_name}, ${game_name}`);

    showError(`Connecting to server machine...`);
    console.log(`Connecting to ws: ${ws_endpoint}`);

    ws = new WebSocket(ws_endpoint);

    ws.addEventListener("open", (event) => {
        ws.send(JSON.stringify({
            type: "start",
            id: session_info.id,
            user: user_name,
            game: game_name
        }))
    });

    let video_webrtc_config = {
        meta: { name: `WebClient-Video-${Date.now()}` },
        signalingServerUrl: `${video_signalling_endpoint}`,
    };

    let audio_webrtc_config = {
        meta: { name: `WebClient-Audio-${Date.now()}` },
        signalingServerUrl: `${audio_signalling_endpoint}`,
    };

    ws.addEventListener("message", (event) => {
        console.log(`Received from server: ${event.data}`);
        let msg = JSON.parse(event.data);
        if (msg.result === "ok") {
            console.log("Start acknowledged by server");
            init_stream(video_webrtc_config, audio_webrtc_config);
        }
        else {
            showError("Unexpected message from server:", msg);
        }
    });

    ws.addEventListener("close", (event) => {
        console.log("WebSocket connection closed", event);
        terminateSession();
    });

    ws.addEventListener("error", (event) => {
        console.error("WebSocket error:", event);
        terminateSession();
    });
}

window.addEventListener("DOMContentLoaded", () => {
    document.addEventListener("click", async () => {
        await init();
    }, { once: true });
});