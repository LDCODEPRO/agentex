"""
AGENTE-X Cockpit | Camada de dados
Le exclusivamente das fontes reais (SQLite + .env). Zero Ghost: sem numero
inventado -- onde nao ha dado, retorna None/lista vazia e o frontend mostra "-".
"""
import os
import sqlite3
import sys
from contextlib import contextmanager
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = _ROOT / "02_MEMORY" / "agente_x.db"

sys.path.insert(0, str(_ROOT / "02_MEMORY" / "long_term"))
sys.path.insert(0, str(_ROOT / "01_CORE" / "finance"))
sys.path.insert(0, str(_ROOT / "01_CORE" / "orchestrator"))

from memory_manager import MemoryManager  # noqa: E402
from finance_engine import FinanceEngine  # noqa: E402
from llm_router import LLMRouter  # noqa: E402

mm = MemoryManager()
finance = FinanceEngine()
_router = LLMRouter()


@contextmanager
def _conn():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def _rows(query: str, params: tuple = ()) -> list[dict]:
    with _conn() as conn:
        return [dict(r) for r in conn.execute(query, params).fetchall()]


def _one(query: str, params: tuple = ()):
    with _conn() as conn:
        row = conn.execute(query, params).fetchone()
        return dict(row) if row else None


# ------------------------------------------------------------------
# Visao Geral
# ------------------------------------------------------------------

def overview() -> dict:
    summary = mm.audit_summary()
    fin = finance.summary()
    return {
        "missions": summary["missions"],
        "fila": summary["fila"],
        "logs": summary["logs"],
        "knowledge": summary["knowledge"],
        "finance": {"daily_spend_usd": fin["daily_spend_usd"], "daily_limit_usd": fin["daily_limit_usd"]},
        "kill_switch": os.getenv("AGENTE_X_STOP_ALL_PAID_LLM", "false").lower() == "true",
    }


def recent_activity(limit: int = 8) -> list[dict]:
    return mm.get_recent_logs(limit=limit)


def system_health() -> list[dict]:
    """Checagens reais -- nada aqui e assumido, cada linha e um teste de fato."""
    out = [{"l": "Servidor do Cockpit", "v": "Online", "c": "#34d399"}]

    try:
        _one("SELECT 1")
        out.append({"l": "Banco de Dados", "v": "OK", "c": "#34d399"})
    except Exception:
        out.append({"l": "Banco de Dados", "v": "Erro", "c": "#f87171"})

    ollama_ok = _router._is_ollama_alive()
    out.append({"l": "Ollama", "v": "Disponível" if ollama_ok else "Offline",
                "c": "#34d399" if ollama_ok else "#f87171"})

    bridge_configured = bool(os.getenv("AGENTE_X_BRIDGE_URL"))
    out.append({"l": "Ponte de Assinatura", "v": "Configurada" if bridge_configured else "Não configurada",
                "c": "#34d399" if bridge_configured else "#8b97a7"})

    kill_switch = os.getenv("AGENTE_X_STOP_ALL_PAID_LLM", "false").lower() == "true"
    out.append({"l": "APIs pagas", "v": "Limitadas pelo teto" if kill_switch else "Liberadas",
                "c": "#fbbf24" if kill_switch else "#34d399"})

    return out


# ------------------------------------------------------------------
# Missoes
# ------------------------------------------------------------------

def list_missions(status: str = None, limit: int = 100) -> list[dict]:
    if status and status != "all":
        return _rows(
            "SELECT * FROM missions WHERE status=? ORDER BY id DESC LIMIT ?",
            (status, limit),
        )
    return _rows("SELECT * FROM missions ORDER BY id DESC LIMIT ?", (limit,))


# ------------------------------------------------------------------
# Fila
# ------------------------------------------------------------------

def queue_by_status() -> dict:
    cols = ["QUEUED", "RUNNING", "DONE", "FAILED", "CANCELLED"]
    out = {}
    for c in cols:
        out[c] = _rows(
            "SELECT * FROM fila_execucao WHERE status=? ORDER BY priority ASC, id DESC LIMIT 20",
            (c,),
        )
    return out


# ------------------------------------------------------------------
# Cerebro / LLMs
# ------------------------------------------------------------------

def brain_usage() -> list[dict]:
    """Contagem de chamadas por provider (llm_usage_ledger). Inclui Bridge/Ollama
    (custo 0, ver instrumentacao em llm_router.py) e provedores pagos."""
    return _rows(
        """
        SELECT provider,
               COUNT(*) as calls,
               COALESCE(SUM(real_cost_usd), 0) as cost_usd
        FROM llm_usage_ledger
        WHERE was_blocked = 0
        GROUP BY provider
        ORDER BY calls DESC
        """
    )


# ------------------------------------------------------------------
# Memoria (knowledge)
# ------------------------------------------------------------------

CATEGORY_TABS = [
    ("RULE", "Regras"),
    ("ARCHITECTURE", "Projeto"),
    ("OPERATIONAL_RULES", "Operacional"),
    ("LESSONS_LEARNED", "Erros"),
    ("LLM_CONFIG", "Financeira"),
    ("LLM_PRICES", "Financeira"),
    ("AGENT_PATTERNS", "Conhecimento"),
    ("MODULE_STATUS", "Conhecimento"),
    ("SYSTEM_AUDIT", "Conhecimento"),
    ("LEARNED_RULE", "Regras"),
    ("DIAGNOSTICS", "Conhecimento"),
    ("CONTEXT", "Conhecimento"),
]


def memory_tabs() -> list[str]:
    seen = []
    for _, label in CATEGORY_TABS:
        if label not in seen:
            seen.append(label)
    return seen


def memory_items(tab: str) -> list[dict]:
    categories = [cat for cat, label in CATEGORY_TABS if label == tab]
    if not categories:
        return []
    placeholders = ",".join("?" for _ in categories)
    return _rows(
        f"SELECT * FROM knowledge WHERE category IN ({placeholders}) ORDER BY updated_at DESC LIMIT 60",
        tuple(categories),
    )


# ------------------------------------------------------------------
# Logs
# ------------------------------------------------------------------

def logs(level: str = None, limit: int = 200) -> list[dict]:
    return mm.get_recent_logs(limit=limit, level=None if level in (None, "ALL") else level)


# ------------------------------------------------------------------
# Seguranca
# ------------------------------------------------------------------

def blocked_actions(limit: int = 20) -> list[dict]:
    """Bloqueios do safe_gate, logados na tabela logs (source=safe_gate).
    Ver instrumentacao em shell_tool.py / file_tool.py."""
    return _rows(
        "SELECT * FROM logs WHERE source='safe_gate' ORDER BY id DESC LIMIT ?",
        (limit,),
    )


# ------------------------------------------------------------------
# Financeiro
# ------------------------------------------------------------------

def finance_overview() -> dict:
    summary = finance.summary()
    total = _one("SELECT COALESCE(SUM(custo_usd),0) as total FROM financeiro")
    by_provider = _rows(
        """
        SELECT provider, COALESCE(SUM(real_cost_usd),0) as cost_usd
        FROM llm_usage_ledger WHERE was_blocked = 0
        GROUP BY provider ORDER BY cost_usd DESC
        """
    )
    return {**summary, "total_spend_usd": round((total or {}).get("total", 0.0), 6), "by_provider": by_provider}


# ------------------------------------------------------------------
# Configuracoes
# ------------------------------------------------------------------

def _mask(value: str) -> str:
    if not value:
        return "(nao configurado)"
    if len(value) <= 6:
        return "•" * len(value)
    return value[:4] + "•" * 10


def settings() -> list[dict]:
    return [
        {
            "title": "Ambiente",
            "rows": [
                {"k": "Modo", "v": "Produção VPS"},
                {"k": "Ollama Host", "v": os.getenv("OLLAMA_HOST", "-")},
                {"k": "Ollama Modelo", "v": os.getenv("OLLAMA_MODEL", "qwen3:8b")},
            ],
        },
        {
            "title": "Chaves / API",
            "rows": [
                {"k": "DeepSeek", "v": _mask(os.getenv("DEEPSEEK_API_KEY", ""))},
                {"k": "OpenAI", "v": _mask(os.getenv("OPENAI_API_KEY", ""))},
                {"k": "Gemini", "v": _mask(os.getenv("GEMINI_API_KEY", ""))},
                {"k": "Claude", "v": _mask(os.getenv("CLAUDE_API_KEY", ""))},
            ],
        },
        {
            "title": "Ponte de assinatura",
            "rows": [
                {"k": "URL", "v": _mask(os.getenv("AGENTE_X_BRIDGE_URL", ""))},
                {"k": "Prioridade", "v": "Principal (custo zero)"},
            ],
        },
        {
            "title": "Custos",
            "rows": [
                {"k": "Teto diário", "v": f"US$ {os.getenv('AGENTE_X_DAILY_LIMIT_USD', '?')}"},
                {"k": "Hard stop", "v": f"US$ {os.getenv('AGENTE_X_HARD_STOP_USD', '?')}"},
                {"k": "Kill switch (pagos)", "v": os.getenv("AGENTE_X_STOP_ALL_PAID_LLM", "false")},
            ],
        },
        {
            "title": "Banco de Dados",
            "rows": [
                {"k": "Engine", "v": "SQLite"},
                {"k": "Path", "v": os.getenv("SQLITE_PATH", "-")},
            ],
        },
    ]
