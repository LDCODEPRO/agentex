"""
AGENTE-X | Mission Planner
Zero Ghost: Quebra metas complexas em passos executáveis reais.
"""
import logging
from mission_templates import MissionTemplates

logger = logging.getLogger("MissionPlanner")

class MissionPlanner:
    def __init__(self):
        self.templates = MissionTemplates()

    def plan_mission(self, mission_code: str, goal: str) -> dict:
        """
        Gera um plano de execução real.
        Retorna um dicionário com o grafo de dependências e passos.
        """
        logger.info(f"Planejando missão {mission_code}: {goal}")
        plan = self.templates.get_template(goal)
        
        # Inserindo metadados críticos
        plan["mission_code"] = mission_code
        plan["status"] = "MISSION_PLANNED"
        
        logger.info(f"Plano gerado com {len(plan['steps'])} passos.")
        return plan
