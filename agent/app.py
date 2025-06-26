import asyncio
from websockets.asyncio.server import serve
import file_dl
import plugins.baba

async def echo(websocket):
    async for message in websocket:
        await websocket.send(message)


async def main():
    async with serve(echo, "localhost", 8765) as server:
        await server.serve_forever()


if __name__ == "__main__":
    # asyncio.run(main())
    games_repo_path = 'C:\\faks\\master\\cloud_gaming\\agent\\db_games'
    working_folder_path = 'C:\\faks\\master\\cloud_gaming\\agent\\data'
    dl = file_dl.LocalFSGameFileManager(working_folder_path, games_repo_path)
    game_path = dl.install_from_repo('baba')
    runner = plugins.baba.BabaGameModule()
    runner.start_game(game_path)
    
    #import subprocess
    #import pathlib
    #exe_path = pathlib.Path("C:\\faks\\master\\cloud_gaming\\agent\\data\\baba\\Baba Is You.exe")
    #subprocess.Popen([str(exe_path)], cwd=exe_path.parent)