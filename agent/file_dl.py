from abc import ABC, abstractmethod
from pathlib import Path
import zipfile
from minio import Minio, S3Error
import tempfile

class MinioClient:
    def __init__(self, endpoint: str, access_key: str, secret_key: str):
        self.client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=False)
    
    def download(self, bucket: str, object_name: str, local_path: str):
        if not self.client.bucket_exists(bucket):
            raise Exception(f"Bucket {bucket} does not exist")
        self.client.fget_object(bucket, object_name, local_path)
    
    def upload(self, bucket: str, object_name: str, local_path: str):
        if not self.client.bucket_exists(bucket):
            raise Exception(f"Bucket {bucket} does not exist")
        self.client.fput_object(bucket, object_name, local_path)

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
        self.minio_client = MinioClient(minio_endpoint, minio_access_key, minio_secret_key)
        self.minio_bucket = minio_bucket

    def install_from_repo(self, game: str) -> Path:
        dest_path = self.working_folder_path / game

        if self.game_is_downloaded(game):
            return dest_path

        zip_file_path = dest_path.with_suffix('.zip')
        self.minio_client.download(self.minio_bucket, f'{game}.zip', str(zip_file_path))

        with zipfile.ZipFile(zip_file_path) as zip:
            zip.extractall(dest_path)

        zip_file_path.unlink(missing_ok=True)

        return dest_path

class SaveFileManager(ABC):
    @abstractmethod
    def download_save(self, game: str, user: str) -> Path: ...

    @abstractmethod
    def upload_save(self, game: str, user: str, local_path: Path): ...


class MinioSaveFileManager(SaveFileManager):
    def __init__(self, minio_endpoint: str, minio_access_key: str, minio_secret_key: str, minio_bucket: str):
        super().__init__()
        self.minio_client = MinioClient(minio_endpoint, minio_access_key, minio_secret_key)
        self.minio_bucket = minio_bucket

    def download_save(self, game: str, user: str) -> Path | None:
        temp_dir = Path(tempfile.gettempdir())
        local_path = temp_dir / f'{game}_{user}_save.zip'

        try:
            self.minio_client.download(self.minio_bucket, f'saves/{game}/{user}.zip', str(local_path))
        except S3Error as e:
            if e.code == "NoSuchKey":
                return None
            raise e

        extract_path = temp_dir / f'{game}_{user}_save'
        with zipfile.ZipFile(local_path) as zip:
            zip.extractall(extract_path)
        local_path.unlink(missing_ok=True)
        return extract_path

    def upload_save(self, game: str, user: str, local_path: Path):
        self.minio_client.upload(self.minio_bucket, f'saves/{game}/{user}.zip', str(local_path))