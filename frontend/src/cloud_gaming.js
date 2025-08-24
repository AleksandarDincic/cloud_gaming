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


function init() {
    let params = window.location.pathname.split('/');
    let user_name = params[1];
    let game_name = params[2];

    console.log(`Cloud gaming input: ${user_name}, ${game_name}`);

    let ws_url = `ws://${window.location.hostname}:8765`;
    showError(`Connecting...`);
    console.log(`Connecting to ws: ${ws_url}`);

    ws = new WebSocket(ws_url);

    ws.addEventListener("open", (event) => {
        ws.send(JSON.stringify({
            type: "start",
            user: user_name,
            game: game_name
        }))
    });

    ws.addEventListener("message", (event) => {
        console.log(`Received from server: ${event.data}`);
    });

    videoElement = document.getElementById("stream_player")

    let session = null;

    let webrtc_config = {
        meta: { name: `WebClient-${Date.now()}` },
        signalingServerUrl: `ws://${window.location.hostname}:8443`,
    };

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
    }, 1 / 60);

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
}

window.addEventListener("DOMContentLoaded", () => {
    document.addEventListener("click", () => {
        init();
    }, { once: true });
});