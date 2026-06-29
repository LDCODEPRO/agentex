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

    def generate_plan(self, macro_goal: str, mission_id: str = "MISSION_BRAIN") -> list:
        """
        Usa o LLM Router para transformar uma string natural de objetivo
        em um JSON estrito de planejamento e dependencias.
        Zero Ghost: chamada real ao router.route() — sem mock ou simulacao.
        """
        sys_prompt = (
            "Voce e o Mission Brain do AGENTE-X.\n"
            "Receba um objetivo e retorne ESTRITAMENTE um array JSON com as tarefas necessarias.\n"
            "Formato obrigatorio:\n"
            "[\n"
            '  {"code": "TASK_1_NAME", "goal": "Descricao do que fazer", "dependencies": []},\n'
            '  {"code": "TASK_2_NAME", "goal": "Descricao", "dependencies": ["TASK_1_NAME"]}\n'
            "]\n"
            "Regras: codigos sem espacos, dependencias so de tasks anteriores, max 10 tasks."
        )
        try:
            # Zero Ghost: chamada real via router.route() — metodo correto do LLMRouter
            result = self.router.route(
                prompt=macro_goal,
                system=sys_prompt,
                agent_name="REACT_ENGINE",
                mission_id=mission_id,
            )
            raw = result.get("response", "")

            # Limpar markdown code blocks se presente
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()

            # Extrair array JSON
            start = raw.find("[")
            end   = raw.rfind("]")
            if start != -1 and end != -1:
                plan = json.loads(raw[start:end + 1])
                self.mm.log("INFO", "MissionBrain",
                            f"Plano gerado: {len(plan)} tasks via {result.get('provider','?')}")
                return plan
            self.mm.log("WARNING", "MissionBrain", f"Resposta LLM nao contem JSON valido: {raw[:200]}")
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

        from mission_state_manager import MissionStateManager
        state_mgr = MissionStateManager()

        for step in plan:
            # Prefixa para evitar colisão
            code = f"{session_prefix}_{step.get('code', 'UNK')}"
            goal = step.get('goal', '')
            
            # Criar fisicamente na tabela missions com status inicial
            state_mgr.transition(code, "MISSION_CREATED", f"Macro-step para: {macro_goal[:50]}")
            
            # 1. Enfileira a tarefa
            self.mm.enqueue_mission(code, payload={"goal": goal, "parent": macro_code})
            
            # 2. Configura grafos
            deps = step.get('dependencies', [])
            for d in deps:
                d_code = f"{session_prefix}_{d}"
                self.graph.add_dependency(code, d_code)
                
        self.mm.log("INFO", "MissionBrain", f"Plano com {len(plan)} submateriais injetado no Grafo.")
        return True

