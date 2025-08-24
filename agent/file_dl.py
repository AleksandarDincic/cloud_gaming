from abc import ABC, abstractmethod
from pathlib import Path
import zipfile

class GameFileManager(ABC):
    def __init__(self, working_folder_path: str):
        super().__init__()
        self.working_folder_path = Path(working_folder_path)

    def game_is_downloaded(self, game: str) -> bool:
        return (self.working_folder_path / game).exists()

    @abstractmethod
    def install_from_repo(self, game: str) -> Path: ...


class LocalFSGameFileManager(GameFileManager):
    def __init__(self, working_folder_path: str, games_repo_path: str):
        super().__init__(working_folder_path)
        self.games_repo_path = Path(games_repo_path)

    def install_from_repo(self, game: str) -> Path:
        dest_path = self.working_folder_path / game

        if self.game_is_downloaded(game):
            return dest_path

        zip_file_path = self.games_repo_path / f'{game}.zip'
        if not zip_file_path.is_file():
            raise Exception(f"Game {game} not in repo")

        
        with zipfile.ZipFile(zip_file_path) as zip:
            zip.extractall(dest_path)

        return dest_path

class SaveFileManager(ABC):
    pass

class LocalFSSaveFileManager(SaveFileManager):
    pass