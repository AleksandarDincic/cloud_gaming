let params = window.location.pathname.split('/');
let user_name = params[1];
let game_name = params[2];

console.log(`working ${user_name}, ${game_name}`);

let ws_url = `ws://${window.location.hostname}:8765`;
console.log(`connecting to ws: ${ws_url}`);

let socket = new WebSocket(ws_url);

socket.addEventListener("open", (event) => {
    socket.send(JSON.stringify({
        type: "start",
        user: user_name,
        game: game_name
    }))
});

socket.addEventListener("message", (event) => {
    console.log(`Received from server: ${event.data}`);
    document.getElementById("server_msg").textContent = event.data;
});