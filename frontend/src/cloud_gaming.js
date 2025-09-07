let videoElement = null;
let ws = null;

let keys_bit_mask = new Uint8Array(32);
let mouse_buttons = 0;
let mouse_dx = 0, mouse_dy = 0;
let mouse_wheel = 0;

let previous_input_keys = new Uint8Array(32);
let previous_mouse_buttons = 0;

let input_packet = new Uint8Array(56); // 32 bytes for keys + 16 bytes for mouse data + 8 bytes for timestamp

const SEND_ON_STATE_CHANGE = true;

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
    if (!force) {
        if (document.pointerLockElement !== videoElement)  {
            console.log("Pointer lock not on video, not sending")
            return;
        }

        if (ws.readyState !== WebSocket.OPEN) {
            console.log("Websocket not open, not sending")
            return;
        }

        if (SEND_ON_STATE_CHANGE && !stateChanged()) {
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

async function init_stream(webrtc_config) {
    videoElement = document.getElementById("stream_player")

    let session = null;

    let webrtc_api = new GstWebRTCAPI(webrtc_config)

    const listener = {
        producerAdded: function (producer) {
            const producerId = producer.id

            console.log(`Adding producer ${producerId}`);

            if (session) {
                console.log("New producer was added but session is already running");
                return;
            }

            session = webrtc_api.createConsumerSession(producerId);

            session.mungeStereoHack = true;

            session.addEventListener("error", (event) => {
                console.error(event.message, event.error);
            });

            session.addEventListener("closed", () => {
                videoElement.pause();
                videoElement.srcObject = null;
                session = null;
                showError("Session closed");
            });

            session.addEventListener("streamsChanged", () => {
                const streams = session.streams;
                if (streams.length > 0) {
                    videoElement.srcObject = streams[0];
                    showError("");
                    videoElement.play().catch(err => {
                        showError("Autoplay error: " + err.message);
                    });
                }
            });

            session.connect();
        },

        producerRemoved: function (producer) {
            showError("Producer removed, should clear everything");
        }
    };

    webrtc_api.registerPeerListener(listener);
        for (const producer of webrtc_api.getAvailableProducers()) {
        listener.producerAdded(producer);
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

async function init() {
    let params = window.location.pathname.split('/');
    let user_name = params[1];
    let game_name = params[2];

    let session_info = null;
    try {
        session_info = await createSession(`http://${window.location.hostname}:3001/create_session?user=${user_name}&game=${game_name}`);
    }
    catch (e) {
        showError(`Failed to create session: ${e.message}`);
        return;
    }

    console.log("Session info:", session_info);
    // session_info is already a JavaScript object, no need to parse

    let ws_endpoint = session_info.ws_endpoint;
    let signalling_endpoint = session_info.signalling_endpoint;

    console.log(`Cloud gaming input: ${user_name}, ${game_name}`);

    showError(`Connecting...`);
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

    let webrtc_config = {
        meta: { name: `WebClient-${Date.now()}` },
        signalingServerUrl: `${signalling_endpoint}`,
    };

    ws.addEventListener("message", (event) => {
        console.log(`Received from server: ${event.data}`);
        let msg = JSON.parse(event.data);
        if (msg.result === "ok") {
            console.log("Start acknowledged by server");
            init_stream(webrtc_config);
        }
        else {
            showError("Unexpected message from server:", msg);
        }
    });
}

window.addEventListener("DOMContentLoaded", () => {
    document.addEventListener("click", async () => {
        await init();
    }, { once: true });
});