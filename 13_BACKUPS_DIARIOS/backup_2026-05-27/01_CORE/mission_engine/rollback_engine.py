"""
AGENTE-X | Rollback Engine
Retorna o estado ao anterior ou limpa side-effects em caso de falha crítica.
"""
import logging
from mission_state_manager import MissionStateManager

logger = logging.getLogger("RollbackEngine")

class RollbackEngine:
    def __init__(self):
        self.state = MissionStateManager()

    def execute_rollback(self, mission_code: str, reason: str):
        logger.warning(f"Iniciando ROLLBACK para missão {mission_code} devido a: {reason}")
        self.state.transition(mission_code, "MISSION_ROLLBACK", f"Rollback trigger: {reason}")
        
        # Em fase 5 aqui reverteria DB states, deletaria arquivos parciais, etc.
        # Por enquanto logamos a reversão sistêmica e travamos o estado.
        logger.info(f"ROLLBACK concluído para {mission_code}.")
        self.state.mm.log("WARNING", "RollbackEngine", f"Rollback executado em {mission_code}")
        
        # Opcional: Se rollback concluído com segurança, transita para FAILED
        self.state.transition(mission_code, "MISSION_FAILED", "Falhou com Rollback.")
