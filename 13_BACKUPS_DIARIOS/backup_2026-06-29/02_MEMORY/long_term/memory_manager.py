"""
AGENTE-X | Memory Manager — SQLite Interface
CRUD real para todas as tabelas do agente_x.db.
Princípio Zero Ghost: operações reais, sem retorno de dados mockados.
"""

import sqlite3
import json
import uuid
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = _ROOT / "02_MEMORY" / "agente_x.db"

logger = logging.getLogger("MemoryManager")


class MemoryManager:
    """
    Interface de memória de longo prazo sobre SQLite.
    Uso: instanciar e chamar os métodos. Thread-safe com check_same_thread=False.
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        if not db_path.exists():
            # Suporte a import direto (sem package) e como módulo
            try:
                from .db_init import init_database
            except ImportError:
                from db_init import init_database
            init_database(db_path)

    # ------------------------------------------------------------------
    # Context manager para conexões
    # ------------------------------------------------------------------

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # MISSIONS
    # ------------------------------------------------------------------

    def create_mission(self, code: str, title: str) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO missions (code, title) VALUES (?, ?)",
                (code, title),
            )
            logger.info("Missão criada: %s — %s", code, title)
            return cur.lastrowid

    def update_mission_status(
        self,
        code: str,
        status: str,
        summary: Optional[str] = None,
    ) -> None:
        valid = {"PENDING", "IN_PROGRESS", "DONE", "FAILED"}
        if status not in valid:
            raise ValueError(f"Status inválido: {status}. Válidos: {valid}")

        ts_field = None
        if status == "IN_PROGRESS":
            ts_field = "started_at"
        elif status in ("DONE", "FAILED"):
            ts_field = "finished_at"

        with self._conn() as conn:
            if ts_field:
                conn.execute(
                    f"UPDATE missions SET status=?, {ts_field}=strftime('%Y-%m-%dT%H:%M:%S','now'), summary=COALESCE(?,summary) WHERE code=?",
                    (status, summary, code),
                )
            else:
                conn.execute(
                    "UPDATE missions SET status=?, summary=COALESCE(?,summary) WHERE code=?",
                    (status, summary, code),
                )
        logger.info("Missão %s → %s", code, status)

    def get_mission(self, code: str) -> Optional[dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM missions WHERE code=?", (code,)
            ).fetchone()
            return dict(row) if row else None

    # ------------------------------------------------------------------
    # SESSIONS
    # ------------------------------------------------------------------

    def start_session(self, provider: str, model: str, metadata: dict = None) -> str:
        session_id = str(uuid.uuid4())
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO sessions (session_id, provider, model, metadata) VALUES (?,?,?,?)",
                (session_id, provider, model, json.dumps(metadata or {})),
            )
        logger.info("Sessão iniciada: %s via %s/%s", session_id, provider, model)
        return session_id

    def end_session(self, session_id: str, total_turns: int) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE sessions SET ended_at=strftime('%Y-%m-%dT%H:%M:%S','now'), total_turns=? WHERE session_id=?",
                (total_turns, session_id),
            )

    # ------------------------------------------------------------------
    # LOGS
    # ------------------------------------------------------------------

    def log(
        self,
        level: str,
        source: str,
        message: str,
        payload: dict = None,
    ) -> None:
        valid_levels = {"INFO", "WARNING", "ERROR", "CRITICAL"}
        level = level.upper()
        if level not in valid_levels:
            level = "INFO"
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO logs (level, source, message, payload) VALUES (?,?,?,?)",
                (level, source, message, json.dumps(payload) if payload else None),
            )

    def get_recent_logs(self, limit: int = 50, level: Optional[str] = None) -> list[dict]:
        with self._conn() as conn:
            if level:
                rows = conn.execute(
                    "SELECT * FROM logs WHERE level=? ORDER BY id DESC LIMIT ?",
                    (level.upper(), limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM logs ORDER BY id DESC LIMIT ?", (limit,)
                ).fetchall()
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # KNOWLEDGE
    # ------------------------------------------------------------------

    def upsert_knowledge(
        self,
        category: str,
        key: str,
        value: str,
        source: str = None,
        confidence: float = 1.0,
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO knowledge (category, key, value, source, confidence)
                VALUES (?,?,?,?,?)
                ON CONFLICT(category, key) DO UPDATE SET
                    value=excluded.value,
                    source=COALESCE(excluded.source, source),
                    confidence=excluded.confidence,
                    updated_at=strftime('%Y-%m-%dT%H:%M:%S','now')
                """,
                (category, key, value, source, confidence),
            )
        logger.info("Conhecimento upsert: [%s] %s", category, key)

    def get_knowledge(self, category: str, key: str) -> Optional[dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM knowledge WHERE category=? AND key=?",
                (category, key),
            ).fetchone()
            return dict(row) if row else None

    def search_knowledge(self, category: str) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM knowledge WHERE category=? ORDER BY updated_at DESC",
                (category,),
            ).fetchall()
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # FILA DE EXECUÇÃO
    # ------------------------------------------------------------------

    def enqueue_mission(
        self, mission_code: str, priority: int = 5, payload: dict = None
    ) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO fila_execucao (mission_code, priority, payload) VALUES (?,?,?)",
                (mission_code, priority, json.dumps(payload or {})),
            )
            return cur.lastrowid

    def dequeue_next(self) -> Optional[dict]:
        """Pega a próxima missão da fila por prioridade."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM fila_execucao WHERE status='QUEUED' ORDER BY priority ASC, id ASC LIMIT 1"
            ).fetchone()
            if row:
                conn.execute(
                    "UPDATE fila_execucao SET status='RUNNING', started_at=strftime('%Y-%m-%dT%H:%M:%S','now') WHERE id=?",
                    (row["id"],),
                )
                return dict(row)
            return None

    def finish_queue_item(self, item_id: int, status: str = "DONE") -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE fila_execucao SET status=?, finished_at=strftime('%Y-%m-%dT%H:%M:%S','now') WHERE id=?",
                (status, item_id),
            )

    # ------------------------------------------------------------------
    # Auditoria
    # ------------------------------------------------------------------

    def audit_summary(self) -> dict:
        with self._conn() as conn:
            def count(table, where="1=1"):
                return conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}").fetchone()[0]

            return {
                "missions": {
                    "total": count("missions"),
                    "done": count("missions", "status='DONE'"),
                    "in_progress": count("missions", "status='IN_PROGRESS'"),
                    "failed": count("missions", "status='FAILED'"),
                },
                "sessions": count("sessions"),
                "logs": {
                    "total": count("logs"),
                    "errors": count("logs", "level='ERROR'"),
                    "critical": count("logs", "level='CRITICAL'"),
                },
                "knowledge": count("knowledge"),
                "fila": {
                    "queued": count("fila_execucao", "status='QUEUED'"),
                    "running": count("fila_execucao", "status='RUNNING'"),
                },
            }


if __name__ == "__main__":
    mm = MemoryManager()
    print("MemoryManager inicializado.")
    print("Resumo do banco:", mm.audit_summary())
