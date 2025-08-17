import game_module
from subprocess import Popen
from pathlib import Path

EXE_NAME = 'SH.exe'

class GameModule(game_module.GameModuleBase):
    def start_game(self, game_folder_path: Path) -> Popen:
        full_exe_path = game_folder_path / EXE_NAME
        print(f"Running SUPERHOT at {str(full_exe_path)}")
        return Popen([str(full_exe_path)], cwd=full_exe_path.parent)