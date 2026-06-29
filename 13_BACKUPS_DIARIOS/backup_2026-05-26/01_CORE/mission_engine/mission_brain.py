"""
AGENTE-X | Mission Brain
O córtex cognitivo que ingere Macro Objetivos, processa via LLM e os quebra
em submateriais encadeados no Dependency Graph.
"""
import sys
import json
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT / "02_MEMORY" / "long_term"))
sys.path.insert(0, str(_ROOT / "01_CORE" / "orchestrator"))

from memory_manager import MemoryManager
from dependency_graph import DependencyGraph
from llm_router import LLMRouter

class MissionBrain:
    def __init__(self):
        self.mm = MemoryManager()
        self.graph = DependencyGraph()
        self.router = LLMRouter()

    def generate_plan(self, macro_goal: str) -> list:
        """
        Usa o LLM Router para transformar uma string natural de objetivo
        em um JSON estrito de planejamento e dependências.
        """
        sys_prompt = '''Você é o Mission Brain.
Receba um objetivo e retorne ESTRITAMENTE um array JSON contendo as tarefas necessárias.
Formato:
[
  {
    "code": "TASK_1_NAME",
    "goal": "Descriçao do que fazer",
    "dependencies": []
  },
  {
    "code": "TASK_2_NAME",
    "goal": "Descriçao",
    "dependencies": ["TASK_1_NAME"]
  }
]
'''
        # Na fase de teste isolado ou sem modelo forte online, podemos mockar
        # ou evocar a chamada real do router.
        try:
            res = self.router.chat(prompt=macro_goal, system_prompt=sys_prompt)
            # Tentativa de parsing do JSON cru
            # Aqui deveríamos limpar crases Markdown, mas vamos assumir que o llm_router faz isso
            start = res.find("[")
            end = res.rfind("]")
            if start != -1 and end != -1:
                return json.loads(res[start:end+1])
            return []
        except Exception as e:
            self.mm.log("ERROR", "MissionBrain", f"Falha na quebra LLM: {e}")
            return []

    def ingest_plan(self, plan: list, macro_goal: str = "") -> bool:
        """
        Recebe o array JSON, insere no Memory Manager e linka no Dependency Graph.
        Retorna True se bem sucedido.
        """
        if not plan:
            return False
            
        session_prefix = f"MACRO_{int(time.time())}"
        
        # Opcional: Registrar a macro-missão "mãe"
        macro_code = f"{session_prefix}_PARENT"
        self.mm.enqueue_mission(macro_code, payload={"goal": macro_goal}, priority=9)
        self.mm.log("INFO", "MissionBrain", f"Macro Ingested: {macro_code}")

        for step in plan:
            # Prefixa para evitar colisão
            code = f"{session_prefix}_{step.get('code', 'UNK')}"
            goal = step.get('goal', '')
            
            # 1. Enfileira a tarefa
            self.mm.enqueue_mission(code, payload={"goal": goal, "parent": macro_code})
            
            # 2. Configura grafos
            deps = step.get('dependencies', [])
            for d in deps:
                d_code = f"{session_prefix}_{d}"
                self.graph.add_dependency(code, d_code)
                
        self.mm.log("INFO", "MissionBrain", f"Plano com {len(plan)} submateriais injetado no Grafo.")
        return True
