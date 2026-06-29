"""
AGENTE-X | Mission Engine
O motor principal para o ciclo de vida completo de uma Missão.
Mapeia de META -> PLANEJAMENTO -> EXECUÇÃO -> VALIDAÇÃO.
"""
import time
import logging
from mission_planner import MissionPlanner
from mission_executor import MissionExecutor
from mission_state_manager import MissionStateManager
from mission_validator import MissionValidator

logger = logging.getLogger("MissionEngine")

class MissionEngine:
    def __init__(self):
        self.planner = MissionPlanner()
        self.executor = MissionExecutor()
        self.state = MissionStateManager()
        self.validator = MissionValidator()

    def run_mission(self, mission_code: str, goal: str) -> dict:
        """Fluxo completo de missão Zero Ghost."""
        logger.info(f"Iniciando missão {mission_code}: {goal}")
        
        self.state.transition(mission_code, "MISSION_CREATED")
        
        # Planejamento
        plan = self.planner.plan_mission(mission_code, goal)
        self.state.transition(mission_code, "MISSION_PLANNED", f"Passos gerados: {len(plan['steps'])}")
        
        self.state.transition(mission_code, "MISSION_RUNNING")
        
        step_results = []
        context = {}
        
        for step in plan["steps"]:
            # Executar passo
            result = self.executor.execute_step(step, context)
            
            # Validar passo
            is_valid = self.validator.validate_step(step, result)
            result["validated"] = is_valid
            
            step_results.append(result)
            
            if not is_valid:
                logger.error(f"Falha ou bloqueio na missão {mission_code} (Step: {step['id']})")
                self.state.transition(mission_code, "MISSION_FAILED", f"Falha no step {step['id']}")
                return {"status": "FAILED", "code": mission_code, "results": step_results}
                
            # Atualizar contexto para o próximo passo
            context[step["id"]] = result["output"]
            
        # Validação final da missão
        if self.validator.validate_mission(plan, step_results):
            self.state.transition(mission_code, "MISSION_VALIDATED", "Missão completa e validada com sucesso.")
            return {"status": "SUCCESS", "code": mission_code, "results": step_results}
        else:
            self.state.transition(mission_code, "MISSION_FAILED", "Falha na validação final da missão.")
            return {"status": "FAILED", "code": mission_code, "results": step_results}

if __name__ == "__main__":
    print("Testando Mission Engine localmente...")
    engine = MissionEngine()
    result = engine.run_mission(f"TEST_{int(time.time())}", "Executar auditoria simples no sistema")
    print(f"Resultado final: {result['status']}")
