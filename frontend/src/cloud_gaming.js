let videoElement = null;
let ws = null;

let keys_bit_mask = new Uint8Array(32);
let mouse_buttons = 0;
let mouse_dx = 0, mouse_dy = 0;
let mouse_wheel = 0;

let previous_input_keys = new Uint8Array(32);

let input_packet = new Uint8Array(32);

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
  return false;
}


function init() {
    let params = window.location.pathname.split('/');
    let user_name = params[1];
    let game_name = params[2];

    console.log(`Cloud gaming input: ${user_name}, ${game_name}`);

    let ws_url = `ws://${window.location.hostname}:8765`;
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
        document.getElementById("error").textContent = event.data;
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
                console.error("Session closed");
            });

            session.addEventListener("streamsChanged", () => {
                const streams = session.streams;
                if (streams.length > 0) {
                    videoElement.srcObject = streams[0];
                    videoElement.play().catch(err => {
                        console.error("Autoplay error:", err.name, err.message);
                    });
                }
            });

            session.connect();
        },

        producerRemoved: function (producer) {
            console.error("Producer removed, should clear everything")
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

    addEventListener("keydown", e => setKey(e.keyCode, true),  {passive:true});
    addEventListener("keyup",   e => setKey(e.keyCode, false), {passive:true});

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

        input_packet.set(keys_bit_mask);

        ws.send(input_packet);

        previous_input_keys.set(keys_bit_mask);
    }, 1 / 60);
}

window.addEventListener("DOMContentLoaded", () => {
    document.addEventListener("click", () => {
        init();
    }, { once: true });
});