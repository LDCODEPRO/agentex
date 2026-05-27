"""
AGENTE-X | Execution Validator
Garante que comandos rodaram e geraram logs esperados.
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT / "02_MEMORY" / "long_term"))

from memory_manager import MemoryManager

class ExecutionValidator:
    def __init__(self):
        self.mm = MemoryManager()
        
    def validate_log_generated(self, source: str, min_level: str = "INFO") -> bool:
        logs = self.mm.get_recent_logs(limit=50)
        for log in logs:
            if log.get("source") == source:
                return True
        return False
