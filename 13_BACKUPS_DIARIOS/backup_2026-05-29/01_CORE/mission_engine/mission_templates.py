"""
AGENTE-X | Mission Templates
Gera planos de execucao para missoes.
Zero Ghost: usa LLM real via LLMRouter quando disponivel.
Fallback honesto: estrutura generica documentada, sem fabricacao de dados.
"""
import sys
import logging
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT / "01_CORE" / "orchestrator"))

logger = logging.getLogger("MissionTemplates")

# Templates estaticos como fallback honesto (nao sao dados fabricados —
# sao estruturas vazias que o executor preencherá com conteúdo real)
_STATIC_TEMPLATES = {
    "audit": [
        {"id": "step_1", "task": "Coletar evidencias do disco e banco de dados"},
        {"id": "step_2", "task": "Analisar estrutura e gerar log de conformidade"},
        {"id": "step_3", "task": "Redigir relatorio final em 08_AUDITS"},
    ],
    "backup": [
        {"id": "step_1", "task": "Verificar integridade dos arquivos criticos"},
        {"id": "step_2", "task": "Executar SaveManager com backup local + GitHub"},
        {"id": "step_3", "task": "Validar manifesto do backup gerado"},
    ],
    "diagnose": [
        {"id": "step_1", "task": "Executar agente_diagnostico.py e coletar score"},
        {"id": "step_2", "task": "Identificar modulos com problemas"},
        {"id": "step_3", "task": "Propor e executar correcoes para itens abaixo de 100/100"},
    ],
    "generic": [
        {"id": "step_1", "task": "Analise e planejamento da tarefa"},
        {"id": "step_2", "task": "Execucao principal"},
        {"id": "step_3", "task": "Validacao e registro do resultado"},
    ],
}


class MissionTemplates:

    def _detect_type(self, goal: str) -> str:
        """Detecta o tipo de missao pelo objetivo (heuristica real)."""
        g = goal.lower()
        if any(w in g for w in ("auditoria", "audit", "verificar", "check")):
            return "audit"
        if any(w in g for w in ("backup", "salvar", "save", "commit")):
            return "backup"
        if any(w in g for w in ("diagnose", "diagnostico", "status", "saude")):
            return "diagnose"
        return "generic"

    def get_template(self, goal: str) -> dict:
        """
        Gera plano de execucao para o objetivo dado.
        Estrategia:
          1. Tenta gerar via LLM real (router.route)
          2. Se LLM indisponivel, usa template estatico honesto com goal inserido
        Zero Ghost: o fallback estatico e documentado como tal — nunca apresentado como resultado LLM.
        """
        # Tentativa 1: LLM real
        try:
            from llm_router import LLMRouter
            import json as _json

            router = LLMRouter()
            system = (
                "Voce e o Mission Planner do AGENTE-X.\n"
                "Dado um objetivo, retorne APENAS um JSON com lista de steps.\n"
                "Formato: {\"steps\": [{\"id\": \"step_1\", \"task\": \"descricao\"}, ...]}\n"
                "Maximo 5 steps. Sem texto extra. Sem markdown."
            )
            result = router.route(
                prompt=f"Planeje a missao: {goal}",
                system=system,
                agent_name="REACT_ENGINE",
                mission_id="MISSION_PLANNER",
            )
            raw = result.get("response", "").strip()
            # Limpar markdown
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:].strip()
                elif raw.startswith("\n"):
                    raw = raw[1:].strip()
            start = raw.find("{")
            end   = raw.rfind("}")
            if start != -1 and end != -1:
                plan = _json.loads(raw[start:end + 1])
                if "steps" in plan and isinstance(plan["steps"], list) and plan["steps"]:
                    logger.info("Plano LLM gerado via %s: %d steps", result.get("provider"), len(plan["steps"]))
                    return {"steps": plan["steps"], "source": f"LLM:{result.get('provider','?')}"}
        except Exception as e:
            logger.warning("LLM indisponivel para planejamento (%s) — usando template estatico", e)

        # Fallback honesto: template estatico documentado
        mission_type = self._detect_type(goal)
        steps = [
            {"id": s["id"], "task": s["task"].replace("da tarefa", f"de: {goal[:60]}")}
            for s in _STATIC_TEMPLATES.get(mission_type, _STATIC_TEMPLATES["generic"])
        ]
        logger.info("Template estatico '%s' usado para: %s", mission_type, goal[:60])
        return {"steps": steps, "source": f"STATIC_TEMPLATE:{mission_type}"}
