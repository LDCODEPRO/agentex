"""
AGENTE-X | Validation Engine
Motor unificado de validação Zero Ghost. Nenhuma tarefa é
marcada como finalizada sem provas reais em múltiplos vetores.
"""
from filesystem_validator import FilesystemValidator
from database_validator import DatabaseValidator
from execution_validator import ExecutionValidator

class ValidationEngine:
    def __init__(self):
        self.fs = FilesystemValidator()
        self.db = DatabaseValidator()
        self.exec = ExecutionValidator()

    def validate_action(self, validations: dict) -> bool:
        """
        Recebe um dicionário com os vetores de validação exigidos.
        Ex: {"file_exists": "caminho.txt", "db_record": ("tabela", "condicao")}
        Se qualquer um falhar, retorna False.
        """
        if "file_exists" in validations:
            if not self.fs.validate_file_exists(validations["file_exists"]):
                return False
                
        if "file_not_empty" in validations:
            if not self.fs.validate_not_empty(validations["file_not_empty"]):
                return False
                
        if "db_record" in validations:
            table, cond = validations["db_record"]
            if not self.db.validate_record_exists(table, cond):
                return False
                
        if "log_generated" in validations:
            if not self.exec.validate_log_generated(validations["log_generated"]):
                return False
                
        return True
