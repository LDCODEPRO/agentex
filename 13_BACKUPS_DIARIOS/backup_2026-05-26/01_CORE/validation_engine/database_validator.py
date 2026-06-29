"""
AGENTE-X | Database Validator
Comprova alterações no banco de dados.
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT / "02_MEMORY" / "long_term"))

from memory_manager import MemoryManager

class DatabaseValidator:
    def __init__(self):
        self.mm = MemoryManager()
        
    def validate_record_exists(self, table: str, condition: str) -> bool:
        try:
            with self.mm._conn() as conn:
                cursor = conn.cursor()
                cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE {condition}")
                count = cursor.fetchone()[0]
                return count > 0
        except Exception:
            return False
