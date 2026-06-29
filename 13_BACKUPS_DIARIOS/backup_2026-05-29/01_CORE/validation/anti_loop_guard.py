"""
AGENTE-X | AntiLoopGuard
Protege o sistema contra rajadas de chamadas LLM e recursao infinita.
Portado do ZEUS_COMMAND_CENTER (Missao 084.1) - adaptado com caminhos dinamicos.
Dependencias: apenas stdlib (sqlite3, time, os, pathlib).
"""
import time
import sqlite3
from pathlib import Path

from trace_context import TraceContext  # noqa: E402 (sys.path inserido pelo llm_router)

_ROOT = Path(__file__).resolve().parent.parent.parent


class AntiLoopGuard:
    """
    ANTI-LOOP & RATE LIMIT GUARD
    Protege o sistema contra rajadas de chamadas LLM e recursao infinita.

    Verificacoes realizadas em preflight():
      1. Profundidade maxima de chamadas encadeadas (evita recursao infinita)
      2. Maximo de retries por contexto
      3. Rate limit global (chamadas por minuto)
      4. Rate limit por agente (chamadas por minuto)
    """

    MAX_DEPTH = 3
    MAX_RETRIES = 2
    MAX_CALLS_PER_MINUTE_GLOBAL = 20

    # Limites por agente (chamadas por minuto)
    AGENT_LIMITS: dict[str, int] = {
        "AGENTE_X": 10,
        "WHATSAPP": 5,
        "REACT_ENGINE": 8,
        "ORCHESTRATOR": 6,
        "DEFAULT_AGENT": 3,
    }

    def __init__(self, db_path: Path | None = None):
        if db_path is None:
            db_path = _ROOT / "02_MEMORY" / "agente_x.db"
        self.db_path = str(db_path)
        self._ensure_tables()

    def _connect(self):
        """Abre conexao com fallback para /tmp se o caminho principal falhar (ex: NTFS no sandbox)."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("CREATE TABLE IF NOT EXISTS _wtest (x INTEGER)")
            conn.execute("DROP TABLE IF EXISTS _wtest")
            conn.commit()
            return conn
        except Exception:
            import tempfile as _tmp, os as _os
            fallback = _os.path.join(_tmp.gettempdir(), "agente_x_antiloop.db")
            self.db_path = fallback
            return sqlite3.connect(fallback)

    def _ensure_tables(self) -> None:
        """Cria tabela de rate_limit_stats se nao existir."""
        try:
            conn = self._connect()
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rate_limit_stats (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent     TEXT,
                    mission_id TEXT,
                    timestamp REAL,
                    is_paid   INTEGER
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[ANTI-LOOP] Erro ao criar tabelas: {e}")

    def preflight(self, context: "TraceContext", provider: str = "unknown") -> tuple[bool, str]:
        """
        Verifica se a chamada LLM e permitida.
        Retorna (allowed: bool, reason: str).
        """
        # 1. Profundidade (recursao)
        if context.depth > self.MAX_DEPTH:
            return False, (
                f"ANTI_LOOP_GUARD: Profundidade maxima excedida "
                f"({context.depth} > {self.MAX_DEPTH})"
            )

        # 2. Retries
        if context.retry_count > self.MAX_RETRIES:
            return False, (
                f"ANTI_LOOP_GUARD: Maximo de retries atingido "
                f"({context.retry_count} > {self.MAX_RETRIES})"
            )

        # 3. Rate limits via SQLite
        now = time.time()
        one_minute_ago = now - 60

        try:
            conn = self._connect()
            c = conn.cursor()

            # Global
            c.execute(
                "SELECT COUNT(*) FROM rate_limit_stats WHERE timestamp > ?",
                (one_minute_ago,),
            )
            global_count = c.fetchone()[0]
            if global_count >= self.MAX_CALLS_PER_MINUTE_GLOBAL:
                conn.close()
                return False, (
                    f"ANTI_LOOP_GUARD: Rate limit GLOBAL atingido ({global_count} rpm)"
                )

            # Por agente
            agent_tag = context.current_agent.upper()
            limit = self.AGENT_LIMITS.get(agent_tag, self.AGENT_LIMITS["DEFAULT_AGENT"])
            c.execute(
                "SELECT COUNT(*) FROM rate_limit_stats WHERE agent = ? AND timestamp > ?",
                (agent_tag, one_minute_ago),
            )
            agent_count = c.fetchone()[0]

            if agent_count >= limit:
                conn.close()
                # Anomalia grave: rajada acima de 2x o limite
                if agent_count > limit * 2:
                    self._activate_safe_mode_signal()
                return False, (
                    f"ANTI_LOOP_GUARD: Rate limit do agente {agent_tag} "
                    f"atingido ({agent_count} rpm)"
                )

            # Registra a chamada
            is_paid = 1 if provider not in ("ollama", "local") else 0
            c.execute(
                "INSERT INTO rate_limit_stats (agent, mission_id, timestamp, is_paid) "
                "VALUES (?, ?, ?, ?)",
                (agent_tag, context.mission_id, now, is_paid),
            )
            conn.commit()
            conn.close()
            return True, "ALLOW"

        except Exception as e:
            print(f"[ANTI-LOOP] Erro no preflight: {e}")
            # Fallback permissivo: nao travar o sistema por erro de DB
            return True, "ALLOW_ON_ERROR"

    def _activate_safe_mode_signal(self) -> None:
        """Sinaliza anomalia grave via log. Integracao com .env/FinanceEngine a implementar."""
        print(
            "[ANTI-LOOP] !!! ANOMALIA DETECTADA !!! "
            "Rajada critica detectada. Considere ativar AGENTE_X_FINANCIAL_SAFE_MODE=true no .env"
        )

    def clear_old_stats(self) -> None:
        """Remove registros com mais de 1 hora (manutencao periodica)."""
        try:
            conn = self._connect()
            conn.execute(
                "DELETE FROM rate_limit_stats WHERE timestamp < ?",
                (time.time() - 3600,),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

    def stats(self) -> dict:
        """Retorna contagem de chamadas no ultimo minuto por agente."""
        now = time.time()
        one_minute_ago = now - 60
        result: dict = {"global": 0, "agents": {}}
        try:
            conn = self._connect()
            c = conn.cursor()
            c.execute(
                "SELECT COUNT(*) FROM rate_limit_stats WHERE timestamp > ?",
                (one_minute_ago,),
            )
            result["global"] = c.fetchone()[0]
            c.execute(
                "SELECT agent, COUNT(*) FROM rate_limit_stats "
                "WHERE timestamp > ? GROUP BY agent",
                (one_minute_ago,),
            )
            for row in c.fetchall():
                result["agents"][row[0]] = row[1]
            conn.close()
        except Exception:
            pass
        return result
