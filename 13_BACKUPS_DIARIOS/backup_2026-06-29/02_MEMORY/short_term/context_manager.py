"""
AGENTE-X | Context Manager — Working Memory
Inspirado no MEMORY.md do Hermes Agent.
Mantém um snapshot compacto do estado ativo do agente,
injetado em cada turno do LLM.
"""
import json
import time
from pathlib import Path
from typing import Optional

_ROOT = Path(__file__).resolve().parent.parent.parent
MEMORY_FILE = _ROOT / "02_MEMORY" / "short_term" / "MEMORY.md"
MAX_CONTEXT_CHARS = 2500  # similar ao Hermes (2200 chars)


class ContextManager:
    """
    Gerencia o contexto ativo (memória de trabalho) do agente.
    - Mantém as últimas N observações do loop ReAct
    - Resume automaticamente quando excede MAX_CONTEXT_CHARS
    - Persiste em MEMORY.md para continuidade cross-session
    """

    def __init__(self, session_id: str = "default"):
        self.session_id = session_id
        self._events: list[dict] = []
        self._facts: dict[str, str] = {}
        self._current_goal: str = ""
        self._load_from_disk()

    # ------------------------------------------------------------------
    # Estado do agente
    # ------------------------------------------------------------------

    def set_goal(self, goal: str) -> None:
        self._current_goal = goal
        self._add_event("GOAL_SET", goal)
        self._save_to_disk()

    def add_observation(self, tool: str, result: str) -> None:
        truncated = result[:500] + "..." if len(result) > 500 else result
        self._add_event("OBSERVATION", f"[{tool}] {truncated}")
        self._save_to_disk()

    def add_thought(self, thought: str) -> None:
        self._add_event("THOUGHT", thought[:300])

    def remember_fact(self, key: str, value: str) -> None:
        self._facts[key] = value
        self._save_to_disk()

    def get_context_snapshot(self) -> str:
        """
        Retorna o snapshot de contexto formatado para injeção no prompt.
        Limita ao MAX_CONTEXT_CHARS para não inflar o contexto do LLM.
        """
        lines = [
            f"# AGENTE-X | Contexto Ativo",
            f"Sessão: {self.session_id}",
            f"Objetivo atual: {self._current_goal or 'Nenhum definido'}",
        ]

        if self._facts:
            lines.append("\n## Fatos conhecidos:")
            for k, v in list(self._facts.items())[-10:]:
                lines.append(f"- {k}: {v}")

        if self._events:
            lines.append("\n## Histórico recente:")
            for ev in self._events[-15:]:
                lines.append(f"[{ev['type']}] {ev['content']}")

        snapshot = "\n".join(lines)

        # Se muito longo, truncar preservando o mais recente
        if len(snapshot) > MAX_CONTEXT_CHARS:
            snapshot = "...[contexto anterior resumido]\n" + snapshot[-(MAX_CONTEXT_CHARS - 40):]

        return snapshot

    def clear_session(self) -> None:
        """Limpa o estado da sessão atual (mantém fatos permanentes)."""
        self._events = []
        self._current_goal = ""
        self._save_to_disk()

    # ------------------------------------------------------------------
    # Persistência em disco
    # ------------------------------------------------------------------

    def _add_event(self, event_type: str, content: str) -> None:
        self._events.append({
            "type": event_type,
            "content": content,
            "ts": time.strftime("%H:%M:%S"),
        })
        # Manter apenas os últimos 50 eventos em memória
        if len(self._events) > 50:
            self._events = self._events[-50:]

    def _save_to_disk(self) -> None:
        try:
            MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "session_id": self.session_id,
                "current_goal": self._current_goal,
                "facts": self._facts,
                "events": self._events[-20:],  # só os 20 mais recentes no arquivo
                "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
            MEMORY_FILE.write_text(
                f"<!-- AGENTE-X MEMORY.md — NÃO EDITAR MANUALMENTE -->\n"
                f"```json\n{json.dumps(data, ensure_ascii=False, indent=2)}\n```",
                encoding="utf-8",
            )
        except Exception:
            pass  # Falha de disco não pode travar o agente

    def _load_from_disk(self) -> None:
        try:
            if MEMORY_FILE.exists():
                raw = MEMORY_FILE.read_text(encoding="utf-8")
                # Extrair JSON do bloco markdown
                import re
                match = re.search(r"```json\n(.*?)\n```", raw, re.DOTALL)
                if match:
                    data = json.loads(match.group(1))
                    self._current_goal = data.get("current_goal", "")
                    self._facts = data.get("facts", {})
                    self._events = data.get("events", [])
        except Exception:
            pass  # Arquivo corrompido? Começa limpo.


if __name__ == "__main__":
    cm = ContextManager(session_id="test")
    cm.set_goal("Testar o context manager")
    cm.add_observation("file_tool", "Lido arquivo README.md com 500 chars")
    cm.remember_fact("projeto", "AGENTE-X")
    print(cm.get_context_snapshot())
