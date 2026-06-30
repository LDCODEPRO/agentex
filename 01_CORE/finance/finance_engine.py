"""
AGENTE-X | Finance Engine
Portado do COMPLEXO ZEUS (core/finance_engine.py) e adaptado para AGENTE-X.
Circuit breaker financeiro: bloqueia chamadas LLM antes de executar se budget excedido.
Dual ledger SQLite: tabela financeiro + llm_usage_ledger.
Configurado via .env do projeto (variaveis AGENTE_X_DAILY_LIMIT_USD, etc).
"""
import sqlite3
import os
import datetime
from pathlib import Path
from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_ROOT / ".env")


def set_paid_llm_kill_switch(stop: bool) -> bool:
    os.environ["AGENTE_X_STOP_ALL_PAID_LLM"] = "true" if stop else "false"
    return os.environ["AGENTE_X_STOP_ALL_PAID_LLM"] == "true"


class FinanceEngine:
    """
    Gestao financeira soberana do AGENTE-X.
    Circuit breaker: bloqueia chamadas LLM antes da execucao se budget excedido.
    Registra cada centavo no SQLite (tabelas: financeiro + llm_usage_ledger).
    """

    PRICES = {
        # DeepSeek (precos atualizados 2026 — fonte: api-docs.deepseek.com)
        "deepseek-v3":           {"input": 0.14  / 1_000_000, "output": 0.28  / 1_000_000},
        "deepseek-chat":         {"input": 0.14  / 1_000_000, "output": 0.28  / 1_000_000},
        "deepseek-v4-pro":       {"input": 0.14  / 1_000_000, "output": 0.28  / 1_000_000},  # V4 lancou 2026-04-24; preco a CONFIRMAR na fonte oficial
        # Anthropic
        "claude-sonnet-4-6":     {"input": 3.00  / 1_000_000, "output": 15.00 / 1_000_000},
        "claude-haiku-4-5-20251001": {"input": 0.80 / 1_000_000, "output": 4.00 / 1_000_000},
        # OpenAI
        "gpt-4o":                {"input": 2.50  / 1_000_000, "output": 10.00 / 1_000_000},
        "gpt-4o-mini":           {"input": 0.15  / 1_000_000, "output": 0.60  / 1_000_000},
        # Gemini
        "gemini-2.0-flash":      {"input": 0.10  / 1_000_000, "output": 0.40  / 1_000_000},
        "gemini-2.5-flash":      {"input": 0.10  / 1_000_000, "output": 0.40  / 1_000_000},
        # Local
        "ollama":                {"input": 0.0,               "output": 0.0},
        "llama3":                {"input": 0.0,               "output": 0.0},
    }

    def __init__(self, db_path=None):
        self.db_path = db_path or str(_ROOT / "02_MEMORY" / "agente_x.db")
        self.daily_limit = float(os.getenv("AGENTE_X_DAILY_LIMIT_USD", "2.00"))
        self.hard_stop   = float(os.getenv("AGENTE_X_HARD_STOP_USD",   "5.00"))
        self.safe_mode   = os.getenv("AGENTE_X_FINANCIAL_SAFE_MODE", "true").lower() == "true"
        self._ensure_tables()

    def _connect(self):
        """Abre conexao com fallback para /tmp se o caminho principal falhar (ex: NTFS no sandbox)."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("CREATE TABLE IF NOT EXISTS _wtest (x INTEGER)")
            conn.execute("DROP TABLE IF EXISTS _wtest")
            conn.commit()
            return conn
        except Exception:
            import tempfile as _tmp, os as _os
            fallback = _os.path.join(_tmp.gettempdir(), "agente_x_finance.db")
            self.db_path = fallback
            return sqlite3.connect(fallback)

    def _ensure_tables(self):
        try:
            conn = self._connect()
            conn.execute("""
                CREATE TABLE IF NOT EXISTS financeiro (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data TEXT NOT NULL,
                    modelo TEXT NOT NULL,
                    tokens_input INTEGER DEFAULT 0,
                    tokens_output INTEGER DEFAULT 0,
                    custo_usd REAL DEFAULT 0.0,
                    is_estimated INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS llm_usage_ledger (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mission_id TEXT,
                    provider TEXT,
                    model TEXT,
                    purpose TEXT DEFAULT 'GENERAL',
                    prompt_tokens INTEGER DEFAULT 0,
                    completion_tokens INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,
                    real_cost_usd REAL DEFAULT 0.0,
                    estimated_cost_usd REAL DEFAULT 0.0,
                    is_estimated INTEGER DEFAULT 0,
                    was_blocked INTEGER DEFAULT 0,
                    block_reason TEXT,
                    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[FINANCE] Aviso ao criar tabelas: {e}")

    def calculate_cost(self, model, input_tokens, output_tokens):
        key = model.split(":")[-1] if ":" in model else model
        price = self.PRICES.get(key) or self.PRICES.get("gpt-4o-mini")
        return round((input_tokens * price["input"]) + (output_tokens * price["output"]), 8)

    def get_budget_state(self):
        daily = self.get_daily_spend()
        pct = (daily / self.daily_limit * 100) if self.daily_limit > 0 else 0
        if pct >= 100: return "BLOCKED", round(pct, 1)
        if pct > 85:   return "CRITICAL_BUDGET", round(pct, 1)
        if pct > 65:   return "WARNING", round(pct, 1)
        if pct > 30:   return "NORMAL", round(pct, 1)
        return "LOW_USAGE", round(pct, 1)

    def finance_preflight(self, provider, model, est_input=500, est_output=500, mission_id=None, purpose="GENERAL"):
        """
        Circuit breaker: chame antes de qualquer chamada LLM paga.
        Retorna (True, "ALLOW") ou (False, motivo_do_bloqueio).
        """
        # Kill switch vale para tarefas em fila/daemon (custo zero sempre). Chat
        # interativo (purpose=CHAT_INTERACTIVE) tem exceção deliberada do Diretor:
        # respostas em segundos custam fracoes de centavo e ainda respeitam o
        # daily_limit/hard_stop abaixo -- nao e um cheque em branco.
        if (os.getenv("AGENTE_X_STOP_ALL_PAID_LLM", "false").lower() == "true"
                and provider != "ollama"
                and purpose != "CHAT_INTERACTIVE"):
            reason = "Kill switch ativo: AGENTE_X_STOP_ALL_PAID_LLM=true"
            self._log_blocked(provider, model, est_input, est_output, mission_id, purpose, reason)
            return False, reason

        if not self.safe_mode:
            return True, "ALLOW"

        current = self.get_daily_spend()
        est_cost = self.calculate_cost(model, est_input, est_output)

        if (current + est_cost) >= self.hard_stop:
            reason = f"Hard stop atingido: ${current:.4f} + ${est_cost:.6f} >= ${self.hard_stop:.2f}"
            self._log_blocked(provider, model, est_input, est_output, mission_id, purpose, reason)
            return False, reason

        return True, "ALLOW"

    def record_usage(self, provider, model, input_tokens, output_tokens, mission_id=None, purpose="GENERAL"):
        cost = self.calculate_cost(model, input_tokens, output_tokens)
        today = datetime.date.today().isoformat()
        try:
            conn = self._connect()
            conn.execute(
                "INSERT INTO financeiro (data, modelo, tokens_input, tokens_output, custo_usd) VALUES (?,?,?,?,?)",
                (today, model, input_tokens, output_tokens, cost)
            )
            conn.execute(
                """INSERT INTO llm_usage_ledger
                   (mission_id, provider, model, purpose, prompt_tokens, completion_tokens, total_tokens, real_cost_usd)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (mission_id, provider, model, purpose, input_tokens, output_tokens,
                 input_tokens + output_tokens, cost)
            )
            conn.commit()
            conn.close()
            return cost
        except Exception as e:
            print(f"[FINANCE] Erro ao registrar uso: {e}")
            return 0.0

    def _log_blocked(self, provider, model, inp, out, mission_id, purpose, reason):
        try:
            est = self.calculate_cost(model, inp, out)
            conn = self._connect()
            conn.execute(
                """INSERT INTO llm_usage_ledger
                   (mission_id, provider, model, purpose, prompt_tokens, completion_tokens,
                    estimated_cost_usd, was_blocked, block_reason)
                   VALUES (?,?,?,?,?,?,?,1,?)""",
                (mission_id, provider, model, purpose, inp, out, est, reason)
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

    def get_daily_spend(self):
        today = datetime.date.today().isoformat()
        try:
            conn = self._connect()
            row = conn.execute("SELECT SUM(custo_usd) FROM financeiro WHERE data=?", (today,)).fetchone()
            conn.close()
            return round(row[0] or 0.0, 6)
        except Exception:
            return 0.0

    def get_monthly_spend(self):
        month = datetime.date.today().strftime("%Y-%m")
        try:
            conn = self._connect()
            row = conn.execute("SELECT SUM(custo_usd) FROM financeiro WHERE data LIKE ?", (f"{month}%",)).fetchone()
            conn.close()
            return round(row[0] or 0.0, 6)
        except Exception:
            return 0.0

    def summary(self):
        state, pct = self.get_budget_state()
        return {
            "daily_spend_usd":   self.get_daily_spend(),
            "monthly_spend_usd": self.get_monthly_spend(),
            "daily_limit_usd":   self.daily_limit,
            "hard_stop_usd":     self.hard_stop,
            "budget_state":      state,
            "budget_pct":        pct,
            "safe_mode":         self.safe_mode,
            "db_path":           self.db_path,
        }
