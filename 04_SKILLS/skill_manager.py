"""
AGENTE-X | Skill Manager
Inspirado no sistema de auto-aprendizado do Hermes Agent.
Apos tarefas complexas (5+ tool calls), extrai e salva skills reutilizaveis.
Na proxima tarefa similar, carrega as skills relevantes no contexto.
Formato de indice: <available_skills> (padrao Hermes Agent Skills Hub).
"""
import json
import time
import hashlib
from pathlib import Path
from typing import Optional

_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = _ROOT / "04_SKILLS" / "learned"

try:
    import sys as _sys
    _sys.path.insert(0, str(_ROOT / "02_MEMORY" / "vector_memory"))
    from chroma_manager import ChromaManager
except Exception:
    ChromaManager = None



class SkillManager:
    """
    Gerencia o banco de skills do agente.
    Skills sao documentos JSON com: goal_pattern, steps, tools_used, success_rate.
    """

    def __init__(self):
        SKILLS_DIR.mkdir(parents=True, exist_ok=True)
        self._skills: dict[str, dict] = {}
        self._load_all()
        
        try:
            if ChromaManager:
                self.chroma = ChromaManager(collection_name="agente_x_skills")
            else:
                self.chroma = None
        except Exception:
            self.chroma = None

    def _load_all(self) -> None:
        for f in SKILLS_DIR.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                self._skills[data["id"]] = data
            except Exception:
                pass

    def _skill_id(self, goal: str) -> str:
        return hashlib.md5(goal.lower().strip()[:100].encode()).hexdigest()[:12]

    def save_skill(
        self,
        goal: str,
        steps: list,
        tools_used: list,
        final_answer: str,
        success: bool = True,
    ) -> Optional[str]:
        """
        Salva uma skill se a tarefa teve 5+ steps.
        Retorna o ID da skill ou None se nao foi salva.
        """
        if len(steps) < 5:
            return None

        skill_id = self._skill_id(goal)

        if skill_id in self._skills:
            existing = self._skills[skill_id]
            runs = existing.get("runs", 1)
            successes = existing.get("successes", 1)
            if success:
                successes += 1
            runs += 1
            existing["runs"] = runs
            existing["successes"] = successes
            existing["success_rate"] = round(successes / runs, 2)
            existing["last_used"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            self._persist(skill_id, existing)
            return skill_id

        skill = {
            "id": skill_id,
            "goal_pattern": goal[:200],
            "steps": steps[-20:],
            "tools_used": list(set(tools_used)),
            "final_answer_sample": final_answer[:300],
            "success": success,
            "runs": 1,
            "successes": 1 if success else 0,
            "success_rate": 1.0 if success else 0.0,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "last_used": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        self._skills[skill_id] = skill
        self._persist(skill_id, skill)

        # Indexar no ChromaDB
        if self.chroma and self.chroma._available:
            try:
                self.chroma.add_memory(
                    doc_id=f"skill:{skill_id}",
                    text=f"Objetivo: {goal} | Ferramentas: {', '.join(tools_used)}",
                    metadata={"category": "SKILL", "skill_id": skill_id}
                )
            except Exception:
                pass

        return skill_id

    def find_relevant_skills(self, goal: str, limit: int = 3) -> list:
        """
        Retorna skills relevantes para o goal atual.
        Usa busca vetorial se ChromaDB estiver disponível, com fallback para match de palavras-chave.
        """
        # Tenta busca vetorial semântica primeiro
        if self.chroma and self.chroma._available:
            try:
                results = self.chroma.search_memory(query=goal, n_results=limit, where={"category": "SKILL"})
                matched_skills = []
                for r in results:
                    skill_id = r["metadata"].get("skill_id")
                    if skill_id in self._skills:
                        matched_skills.append(self._skills[skill_id])
                if matched_skills:
                    return matched_skills
            except Exception:
                pass

        # Fallback honesto: match simples de palavras-chave
        goal_words = set(goal.lower().split())
        scored = []
        for skill in self._skills.values():
            pattern_words = set(skill["goal_pattern"].lower().split())
            overlap = len(goal_words & pattern_words)
            if overlap > 0:
                scored.append((overlap * skill["success_rate"], skill))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored[:limit]]


    def format_skills_for_prompt(self, goal: str) -> str:
        """
        Formata skills relevantes para injecao no prompt do LLM.
        Formato <available_skills> inspirado no Hermes Agent Skills Hub.
        """
        skills = self.find_relevant_skills(goal)
        if not skills:
            return ""

        lines = [
            "## Skills Aprendidas",
            "Verifique se alguma skill abaixo se aplica ao objetivo atual.",
            "Se sim, siga a estrategia documentada.",
            "",
            "<available_skills>",
        ]
        for s in skills:
            rate = int(s["success_rate"] * 100)
            tools = ", ".join(s["tools_used"]) if s["tools_used"] else "nenhuma"
            lines.append("  " + s["id"] + ":")
            lines.append("    goal: " + s["goal_pattern"][:100])
            lines.append("    tools: " + tools)
            lines.append("    success_rate: " + str(rate) + "%")
            lines.append("    runs: " + str(s.get("runs", 1)))
        lines.append("</available_skills>")
        return "\n".join(lines)

    def _persist(self, skill_id: str, data: dict) -> None:
        try:
            path = SKILLS_DIR / (skill_id + ".json")
            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception:
            pass

    def stats(self) -> dict:
        top = sorted(
            self._skills.values(),
            key=lambda x: x["runs"],
            reverse=True
        )[:5]
        return {
            "total_skills": len(self._skills),
            "skills_dir": str(SKILLS_DIR),
            "top_skills": [
                {"id": s["id"], "goal": s["goal_pattern"][:50], "runs": s["runs"]}
                for s in top
            ],
        }
