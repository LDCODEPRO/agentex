"""
AGENTE-X | Truth Validator
Verifica consistência lógica cruzada.
Exemplo: Se o banco diz 'DONE', o arquivo de log e de evidência precisam existir.
"""
from filesystem_validator import FilesystemValidator
from database_validator import DatabaseValidator

class TruthValidator:
    def __init__(self):
        self.fs = FilesystemValidator()
        self.db = DatabaseValidator()

    def validate_cross_truth(self, table: str, condition: str, filepath: str) -> bool:
        """Retorna True apenas se o estado no banco e o arquivo conferirem (Double-check)"""
        db_ok = self.db.validate_record_exists(table, condition)
        fs_ok = self.fs.validate_file_exists(filepath)
        return db_ok and fs_ok
