import game_module
from subprocess import Popen, CREATE_NEW_CONSOLE
from pathlib import Path

EXE_NAME = 'test.ps1'

class GameModule(game_module.GameModuleBase):
    def start_game(self, game_folder_path: Path) -> Popen:
        full_exe_path = game_folder_path / EXE_NAME
        print(f"Running test script at {str(full_exe_path)}")
        return Popen(["powershell.exe", "-File", str(full_exe_path)], cwd=full_exe_path.parent, creationflags=CREATE_NEW_CONSOLE)