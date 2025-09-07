from abc import ABC, abstractmethod
from pathlib import Path
import zipfile
from minio import Minio

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

class MinioGameFileManager(GameFileManager):
    def __init__(self, working_folder_path: str, minio_endpoint: str, minio_access_key: str, minio_secret_key: str, minio_bucket: str):
        super().__init__(working_folder_path)
        self.minio_client = Minio(minio_endpoint, access_key=minio_access_key, secret_key=minio_secret_key, secure=False)
        self.minio_bucket = minio_bucket

    def install_from_repo(self, game: str) -> Path:
        dest_path = self.working_folder_path / game

        if self.game_is_downloaded(game):
            return dest_path

        zip_file_path = dest_path.with_suffix('.zip')
        if self.minio_client.bucket_exists(self.minio_bucket):
            self.minio_client.fget_object(self.minio_bucket, f'{game}.zip', str(zip_file_path))
        else:
            raise Exception(f"Bucket {self.minio_bucket} does not exist")

        with zipfile.ZipFile(zip_file_path) as zip:
            zip.extractall(dest_path)

        zip_file_path.unlink(missing_ok=True)

        return dest_path

class SaveFileManager(ABC):
    pass

class LocalFSSaveFileManager(SaveFileManager):
    pass