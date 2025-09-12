import os
import re
import json
import shutil
import zipfile
import tempfile
from pathlib import Path
from subprocess import Popen

class GameMetadata:
    def __init__(self, exe_location: str, save_root: str, save_patterns: list):
        self.root = os.path.expandvars(save_root)
        self.exe_location = exe_location
        self.patterns = save_patterns

    @classmethod
    def from_json(cls, json_path: Path):
        with open(json_path, 'r') as f:
            data = json.load(f)
        return cls(
            exe_location=data['exe_location'],
            save_root=data['save_root'],
            save_patterns=data['save_patterns']
        )

class GameManager:
    @staticmethod
    def start_game(game_root_folder: Path, metadata: GameMetadata) -> Popen:
        exe_path = game_root_folder / metadata.exe_location
        cwd = exe_path.parent
        return Popen([str(exe_path)], cwd=str(cwd))

    @staticmethod
    def import_save(source_location: Path, metadata: GameMetadata):
        root = Path(metadata.root)
        
        for pat in metadata.patterns:
            pat_root = root / pat['pattern_root']
            if not pat_root.exists():
                pat_root.mkdir(parents=True, exist_ok=True)
            for f in pat_root.glob(pat['pattern']):
                if f.is_file():
                    f.unlink()

        if not source_location:
            return
        
        for pat in metadata.patterns:
            src_pat_root = source_location / pat['pattern_root']
            for f in src_pat_root.glob(pat['pattern']):
                if f.is_file():
                    rel_path = f.relative_to(source_location)
                    dest_path = root / rel_path
                    shutil.copy2(f, dest_path)

    @staticmethod
    def export_save(metadata: GameMetadata) -> Path:
        root = Path(metadata.root)
        temp_folder = Path(tempfile.mkdtemp())
        zip_path = temp_folder / 'save_export.zip'
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for pat in metadata.patterns:
                pat_root = root / pat['pattern_root']
                for f in pat_root.glob(pat['pattern']):
                    if f.is_file():
                        zipf.write(f, arcname=str(f.relative_to(root)))
        return zip_path
