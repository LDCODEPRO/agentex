"""
AGENTE-X | Rollback Engine
Registra falha critica, sinaliza o estado de rollback no banco e
encerra a missao como FAILED.
Zero Ghost: rollback atual cobre estado DB e logs.
Rollback de arquivos fisicos requer evidencia_path na missao (implementacao futura real).
"""
import sys
import logging
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT / "01_CORE" / "mission_engine"))
sys.path.insert(0, str(_ROOT / "02_MEMORY" / "long_term"))

from mission_state_manager import MissionStateManager

logger = logging.getLogger("RollbackEngine")


class RollbackEngine:
    def __init__(self):
        self.state = MissionStateManager()

    def execute_rollback(self, mission_code: str, reason: str) -> dict:
        """
        Executa rollback da missao:
          1. Transiciona estado para MISSION_ROLLBACK no DB
          2. Registra causa no log persistente
          3. Transiciona para MISSION_FAILED como estado terminal
        Retorna dict com status e acoes executadas.
        """
        logger.warning("Iniciando ROLLBACK para missao %s: %s", mission_code, reason)
        actions = []

        # 1. Marcar como ROLLBACK
        try:
            self.state.transition(mission_code, "MISSION_ROLLBACK", "Rollback: " + reason)
            actions.append("state->MISSION_ROLLBACK")
        except Exception as e:
            logger.error("Erro ao transicionar para MISSION_ROLLBACK: %s", e)

        # 2. Log persistente
        try:
            self.state.mm.log(
                "WARNING", "RollbackEngine",
                "Rollback da missao " + mission_code + ": " + reason
            )
            actions.append("log_persistido")
        except Exception as e:
            logger.error("Erro ao persistir log de rollback: %s", e)

        # 3. Estado terminal FAILED
        try:
            self.state.transition(
                mission_code, "MISSION_FAILED",
                "Encerrado por rollback: " + reason[:200]
            )
            actions.append("state->MISSION_FAILED")
        except Exception as e:
            logger.error("Erro ao transicionar para MISSION_FAILED: %s", e)

        logger.info("Rollback concluido para %s. Acoes: %s", mission_code, actions)
        return {"mission_code": mission_code, "reason": reason, "actions": actions}
