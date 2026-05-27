"""
AGENTE-X | Mission State Manager
Gerencia os estados das missões no banco de dados.
Zero Ghost: Integração real com SQLite.
"""
import sys
from pathlib import Path
from datetime import datetime

_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT / "02_MEMORY" / "long_term"))

from memory_manager import MemoryManager

class MissionStateManager:
    VALID_STATES = [
        "MISSION_CREATED",
        "MISSION_PLANNED",
        "MISSION_QUEUED",
        "MISSION_RUNNING",
        "MISSION_WAITING",
        "MISSION_BLOCKED",
        "MISSION_RETRYING",
        "MISSION_FAILED",
        "MISSION_COMPLETED",
        "MISSION_VALIDATED",
        "MISSION_ROLLBACK"
    ]

    def __init__(self):
        self.mm = MemoryManager()

    def transition(self, mission_code: str, new_state: str, summary: str = None):
        if new_state not in self.VALID_STATES:
            raise ValueError(f"Estado de missão inválido: {new_state}")

        action = ""
        with self.mm._conn() as conn:
            cursor = conn.cursor()
            
            # Verificar se a missão existe
            cursor.execute("SELECT id, status FROM missions WHERE code = ?", (mission_code,))
            row = cursor.fetchone()
    
            if not row:
                # Criar nova missão
                cursor.execute(
                    "INSERT INTO missions (code, title, status) VALUES (?, ?, ?)",
                    (mission_code, f"Mission {mission_code}", new_state)
                )
                action = "created"
            else:
                # Atualizar
                mission_id = row[0]
                cursor.execute(
                    "UPDATE missions SET status = ?, summary = ? WHERE id = ?",
                    (new_state, summary, mission_id)
                )
                action = "updated"

        if action == "created":
            self.mm.log("INFO", "MissionState", f"Missão criada {mission_code} -> {new_state}")
        else:
            self.mm.log("INFO", "MissionState", f"Transição {mission_code} -> {new_state}")

    def get_state(self, mission_code: str) -> str:
        with self.mm._conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM missions WHERE code = ?", (mission_code,))
            row = cursor.fetchone()
            return row[0] if row else None
