"""
AGENTE-X | Dependency Graph
Controla dependências entre missões (mission_parent e childs).
Garante que uma missão só inicia se as dependências validarem.
"""
import json
import logging
from mission_state_manager import MissionStateManager

logger = logging.getLogger("DependencyGraph")

class DependencyGraph:
    def __init__(self):
        self.state = MissionStateManager()

    def add_dependency(self, mission_code: str, dependency_code: str):
        with self.state.mm._conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT dependencies FROM missions WHERE code = ?", (mission_code,))
            row = cursor.fetchone()
            if row:
                deps = json.loads(row[0] or "[]")
                if dependency_code not in deps:
                    deps.append(dependency_code)
                cursor.execute(
                    "UPDATE missions SET dependencies = ? WHERE code = ?",
                    (json.dumps(deps), mission_code)
                )

    def can_start(self, mission_code: str) -> bool:
        """Verifica se todas as dependências estão MISSION_VALIDATED."""
        with self.state.mm._conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT dependencies FROM missions WHERE code = ?", (mission_code,))
            row = cursor.fetchone()
            if row and row[0]:
                deps = json.loads(row[0])
                for dep in deps:
                    status = self.state.get_state(dep)
                    if status != "MISSION_VALIDATED":
                        return False
        return True
