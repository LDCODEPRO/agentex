"""
AGENTE-X | TraceContext
Contexto de rastreamento para chamadas LLM entre agentes.
Previne loops infinitos e recursao profunda.
Portado do ZEUS_COMMAND_CENTER - apenas stdlib (uuid, time, dataclasses).
"""
import uuid
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TraceContext:
    """
    Contexto de rastreamento para chamadas LLM e interacoes entre agentes.
    Evita loops infinitos e recursao profunda.
    """
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_request_id: Optional[str] = None
    mission_id: str = "UNKNOWN"
    origin_agent: str = "DEFAULT_AGENT"
    current_agent: str = "DEFAULT_AGENT"
    depth: int = 0
    retry_count: int = 0
    purpose: str = "GENERAL"
    created_at: float = field(default_factory=time.time)

    def next_step(self, next_agent: str, purpose: Optional[str] = None) -> "TraceContext":
        """Cria um novo contexto para o proximo passo da cadeia."""
        return TraceContext(
            trace_id=self.trace_id,
            request_id=str(uuid.uuid4()),
            parent_request_id=self.request_id,
            mission_id=self.mission_id,
            origin_agent=self.origin_agent,
            current_agent=next_agent,
            depth=self.depth + 1,
            retry_count=0,
            purpose=purpose or self.purpose,
        )

    def next_retry(self) -> "TraceContext":
        """Incrementa o contador de retries para a mesma request."""
        self.retry_count += 1
        return self

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "request_id": self.request_id,
            "parent_request_id": self.parent_request_id,
            "mission_id": self.mission_id,
            "origin_agent": self.origin_agent,
            "current_agent": self.current_agent,
            "depth": self.depth,
            "retry_count": self.retry_count,
            "purpose": self.purpose,
            "created_at": self.created_at,
        }
