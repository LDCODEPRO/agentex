"""
AGENTE-X | Filesystem Validator
Verifica se arquivos realmente existem, sem ilusões.
"""
from pathlib import Path

class FilesystemValidator:
    def validate_file_exists(self, filepath: str) -> bool:
        path = Path(filepath)
        return path.exists() and path.is_file()

    def validate_dir_exists(self, dirpath: str) -> bool:
        path = Path(dirpath)
        return path.exists() and path.is_dir()
        
    def validate_not_empty(self, filepath: str) -> bool:
        path = Path(filepath)
        if not self.validate_file_exists(filepath):
            return False
        return path.stat().st_size > 10
