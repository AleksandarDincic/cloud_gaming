import asyncio
from websockets.asyncio.server import serve
import file_dl
import json
import importlib.util
from pathlib import Path
from game_module import GameModuleBase
from subprocess import Popen
from streaming import start_streaming
from remote_input import handle_packet
from process import wait_for_window, bring_window_to_foreground

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
        self.streaming_process = None


class Config:
    def __init__(self, games_repo_path: str, working_folder_path: str, host_ip: str, host_port: int, audio_device: str):
        self.games_repo_path = games_repo_path
        self.working_folder_path = working_folder_path
        self.host_ip = host_ip
        self.host_port = host_port
        self.audio_device = audio_device

def start_game(config: Config, user: str, game: str) -> Popen:
    dl = file_dl.LocalFSGameFileManager(config.working_folder_path, config.games_repo_path)
    game_path = dl.install_from_repo(game)
    game_module = load_game_module(game_path)
    return game_module.start_game(game_path) # TODO: does this really need game_path as param? why not a field?

def create_ws_handle(config: Config, agent_state: AgentState):

    async def cleanup():
        async with agent_state.lock:
            if agent_state.game_proccess:
                agent_state.game_proccess.terminate()
                agent_state.game_proccess = None
            if agent_state.streaming_process:
                agent_state.streaming_process.terminate()
                agent_state.streaming_process = None
            cleanup_packet = bytes(56)
            handle_packet(cleanup_packet)
            print("Game and streaming processes released. Input cleaned up.")

    async def ws_handle(ws):
        try:
            async with agent_state.lock:
                if agent_state.game_proccess is not None:
                    print(f"A new connection was made but a game is already running. Closing the new connection.")
                    try:
                        await ws.send(json.dumps({
                            "result": "err",
                            "msg": "A session is already running."
                        }))
                    except Exception as e:
                        print(f"Error while sending response to client: {e}")
                    return

                msg = await ws.recv()
                json_msg = json.loads(msg)
                user = json_msg['user']
                game = json_msg['game']
                
                
                if json_msg['type'] == "start":
                    agent_state.game_proccess = start_game(config, user, game)

                    hwnd = wait_for_window(agent_state.game_proccess.pid)

                    if not hwnd:
                        await ws.send(json.dumps({
                            "result": "err",
                            "msg": "Unable to start the game."
                        }))
                        raise Exception("Window not found")

                    bring_window_to_foreground(hwnd)
                    print(f"Streaming window {hwnd} and audio device {audio_device}")
                    agent_state.streaming_process = start_streaming(hwnd, audio_device)
                    await ws.send(json.dumps({
                        "result": "ok",
                    }))

            async for msg in ws:
                if isinstance(msg, bytes):
                    handle_packet(msg)
                else:
                    print(f"New msg: {msg}")
        except Exception as e:
                print(f"Error: {e}. Closing session")
        finally:
            await cleanup()

    return ws_handle


async def main(config: Config):
    agent_state = AgentState()

    async with serve(create_ws_handle(config, agent_state), config.host_ip, config.host_port) as server:
        await server.serve_forever()


if __name__ == "__main__":
    games_repo_path = 'C:\\faks\\master\\cloud_gaming\\agent\\db_games'
    working_folder_path = 'C:\\faks\\master\\cloud_gaming\\agent\\data'
    host_ip = "0.0.0.0"
    host_port = 8765
    audio_device = "{0.0.1.00000000}.{c044b75b-0f4c-483f-ac7c-3e16636b239a}"

    config = Config(games_repo_path, working_folder_path, host_ip, host_port, audio_device)

    asyncio.run(main(config))