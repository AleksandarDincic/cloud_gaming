import asyncio
import configparser
from websockets.asyncio.server import serve
import file_dl
import json
import importlib.util
import redis
import traceback
from pathlib import Path
from dataclasses import dataclass
from game_module import GameModuleBase
from subprocess import Popen
from streaming import start_video_streaming, start_audio_streaming
from remote_input import handle_packet
from process import wait_for_window, bring_window_to_foreground
from game_manager import GameMetadata, GameManager

def load_game_module(game_dir: Path) -> GameModuleBase:
    plugin_file = game_dir / "game.py"

    modname = f"{game_dir.name}_game_module"
    spec = importlib.util.spec_from_file_location(modname, plugin_file)
    module  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    cls = getattr(module, "GameModule", None)
    if cls is None or not issubclass(cls, GameModuleBase):
        raise TypeError(f"{plugin_file} must define class GameModule(GameModuleBase)")
    return cls()

class AgentState:
    def __init__(self):
        self.lock = asyncio.Lock()
        self.game_proccess = None
        self.video_streaming_process = None
        self.audio_streaming_process = None
        self.connection_event = asyncio.Event()  # Event to signal connection

class SessionData:
    def __init__(self, id: str, user: str, game: str):
        self.id = id
        self.user = user
        self.game = game


@dataclass
class Config:
    games_repo_path: str
    working_folder_path: str
    ws_ip: str
    ws_port: int
    reported_ws_endpoint: str
    reported_video_signalling_endpoint: str
    reported_audio_signalling_endpoint: str
    redis_ip: str
    redis_port: int
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str

    @classmethod
    def from_ini(cls, ini_path: str):
        parser = configparser.ConfigParser()
        parser.read(ini_path)
        
        games_repo_path = parser['fs']['games_repo']
        working_folder_path = parser['fs']['working_folder']

        ws_ip = parser['session']['ws_ip']
        ws_port = int(parser['session']['ws_port'])
        reported_ws_endpoint = parser['session']['reported_ws_endpoint']
        reported_video_signalling_endpoint = parser['session']['reported_video_signalling_endpoint']
        reported_audio_signalling_endpoint = parser['session']['reported_audio_signalling_endpoint']

        redis_ip = parser['redis']['host']
        redis_port = int(parser['redis']['port'])

        minio_endpoint = parser['minio']['endpoint']
        minio_access_key = parser['minio']['access_key']
        minio_secret_key = parser['minio']['secret_key']

        return cls(
            games_repo_path=games_repo_path,
            working_folder_path=working_folder_path,
            ws_ip=ws_ip,
            ws_port=ws_port,
            reported_ws_endpoint=reported_ws_endpoint,
            reported_video_signalling_endpoint=reported_video_signalling_endpoint,
            reported_audio_signalling_endpoint=reported_audio_signalling_endpoint,
            redis_ip=redis_ip,
            redis_port=redis_port,
            minio_endpoint=minio_endpoint,
            minio_access_key=minio_access_key,
            minio_secret_key=minio_secret_key
        )

def create_ws_handle(config: Config, agent_state: AgentState, session_data: SessionData):

    game_dl = file_dl.MinioGameFileManager(config.working_folder_path, config.minio_endpoint, config.minio_access_key, config.minio_secret_key, 'games')
    save_dl = file_dl.MinioSaveFileManager(config.minio_endpoint, config.minio_access_key, config.minio_secret_key, 'saves')

    game_metadata = None
    game = None
    user = None

    async def cleanup():
        async with agent_state.lock:
            if agent_state.game_proccess:
                agent_state.game_proccess.terminate()
                agent_state.game_proccess = None
                if game_metadata and game and user:
                    zipped_save = GameManager.export_save(game_metadata)
                    save_dl.upload_save(game, user, zipped_save)
                else:
                    print("Game metadata, game, or user is None; skipping save upload.")
            if agent_state.video_streaming_process:
                agent_state.video_streaming_process.terminate()
                agent_state.video_streaming_process = None
            if agent_state.audio_streaming_process:
                agent_state.audio_streaming_process.terminate()
                agent_state.audio_streaming_process = None
            cleanup_packet = bytes(56)
            handle_packet(cleanup_packet)
            print("Game, video streaming, and audio streaming processes released. Input cleaned up.")

    async def ws_handle(ws):
        nonlocal game_metadata, game, user
        new_session = False
        try:
            try:
                print("Waiting for start message...")
                msg = await asyncio.wait_for(ws.recv(), timeout=5)
            except asyncio.TimeoutError:
                print("Timeout waiting for start message.")
                await ws.send(json.dumps({
                    "result": "err",
                    "msg": "Timeout waiting for start message."
                }))
                return
            json_msg = json.loads(msg)

            if json_msg['type'] != "start":
                print("First message was not start. Received:", json_msg)
                await ws.send(json.dumps({
                    "result": "err",
                    "msg": "First message must be start."
                }))
                return

            user = json_msg.get('user')
            game = json_msg.get('game')

            if user != session_data.user or game != session_data.game or session_data.id != json_msg.get('id'):
                print("Session data mismatch. Received:", json_msg)
                await ws.send(json.dumps({
                    "result": "err",
                    "msg": "Session data mismatch."
                }))
                return

            async with agent_state.lock:
                if agent_state.game_proccess is not None:
                    print(f"A new connection was made but a game is already running. Closing the new connection.")
                    await ws.send(json.dumps({
                        "result": "err",
                        "msg": "A session is already running."
                    }))
                    return

                new_session = True
                agent_state.connection_event.set()

                game_path = game_dl.install_from_repo(game)
                print (f"Game {game} installed to {game_path}")
                game_metadata = GameMetadata.from_json(game_path / "cloud_gaming_metadata.json")
                print(f"Game metadata: {game_metadata}")
                save_path = save_dl.download_save(game, user)

                if save_path:
                    print(f"Existing save downloaded to {save_path}. Importing...")
                else:
                    print("No existing save found.")
                    
                GameManager.import_save(save_path, game_metadata)

                agent_state.game_proccess = GameManager.start_game(game_path, game_metadata)

                hwnd = wait_for_window(agent_state.game_proccess.pid)

                if not hwnd:
                    await ws.send(json.dumps({
                        "result": "err",
                        "msg": "Unable to start the game."
                    }))
                    raise Exception("Window not found")

                bring_window_to_foreground(hwnd)
                print(f"Streaming window {hwnd}")
                agent_state.video_streaming_process = start_video_streaming(hwnd)
                agent_state.audio_streaming_process = start_audio_streaming()
                await ws.send(json.dumps({
                    "result": "ok",
                }))

            async for msg in ws:
                if isinstance(msg, bytes):
                    handle_packet(msg)
                else:
                    print(f"New msg: {msg}")
        except Exception as e:
            traceback.print_exc()
            print(f"Error: {e}. Closing session")
        finally:
            if new_session:
                await cleanup()
                ws.server.close()

    return ws_handle


async def main(config: Config):
    agent_state = AgentState()
    redis_client = redis.Redis(host=config.redis_ip, port=config.redis_port)
    while True:
        try:
            print("Waiting for next session request...")
            _, session_request = redis_client.brpop("sessions", timeout=0)
            session_data = json.loads(session_request)
            print(f"Received session request: {session_data}")
            session_data = SessionData(**session_data)

            redis_client.lpush(f"{session_data.id}", json.dumps({
                "ws_endpoint": config.reported_ws_endpoint,
                "video_signalling_endpoint": config.reported_video_signalling_endpoint,
                "audio_signalling_endpoint": config.reported_audio_signalling_endpoint,
                "id": session_data.id
            }))

            agent_state.connection_event.clear()
            
            ws_handler = create_ws_handle(config, agent_state, session_data)
            async with serve(ws_handler, config.ws_ip, config.ws_port) as server:
                print("WebSocket server started. Waiting for connection...")
                
                try:
                    await asyncio.wait_for(agent_state.connection_event.wait(), timeout=10)
                    print("Connection established. Waiting for session to complete...")
                except asyncio.TimeoutError:
                    print("No connection received within 10 seconds. Canceling session.")
                    server.close()
                
                await server.wait_closed()
                print("WebSocket server closed.")

        except Exception as e:
            print(f"Error connecting to Redis server: {e}. Retrying in 10 seconds...")
            await asyncio.sleep(10)


if __name__ == "__main__":
    config = Config.from_ini('C:/faks/master/cloud_gaming/agent/config.ini')
    
    asyncio.run(main(config))