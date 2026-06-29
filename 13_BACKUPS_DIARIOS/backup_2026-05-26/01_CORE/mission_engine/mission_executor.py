"""
AGENTE-X | Mission Executor
Zero Ghost: Usa o ReActEngine para executar de verdade as tarefas.
"""
import sys
import logging
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT / "01_CORE" / "orchestrator"))

from react_engine import ReActEngine

logger = logging.getLogger("MissionExecutor")

class MissionExecutor:
    def __init__(self):
        self.engine = ReActEngine()

    def execute_step(self, step: dict, context: dict = None) -> dict:
        """
        Executa um passo real usando LLM / Ferramentas via ReActEngine.
        Retorna um dicionário com status e resultado.
        """
        task_desc = step.get("task", "Tarefa desconhecida")
        logger.info(f"Executando step {step.get('id')}: {task_desc}")
        
        try:
            # Em um cenário real, poderiamos compor o goal
            goal = f"{task_desc} (Contexto: {context or ''})"
            result = self.engine.run(goal=goal, verbose=False)
            
            # Se o resultado indica falha (por exemplo, bloqueado)
            if "FALHA CRÍTICA" in result or "SAFE_MODE" in result:
                return {"status": "ERROR", "output": result}
                
            return {"status": "SUCCESS", "output": result}
            
        except Exception as e:
            logger.error(f"Erro ao executar step {step.get('id')}: {e}")
            return {"status": "ERROR", "output": str(e)}
