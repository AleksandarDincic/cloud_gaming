from abc import ABC, abstractmethod
from subprocess import Popen
from pathlib import Path

class GameModuleBase(ABC):
    @abstractmethod
    def start_game(self, game_folder_path: Path) -> Popen: ...