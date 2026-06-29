"""
AGENTE-X | Daily Report Generator
Gera relatório executivo diário em 08_AUDITS/reports/ com dados reais do sistema.
Integrado ao SaveManager e chamável de forma standalone.
Princípio Zero Ghost: todos os dados vêm diretamente do SQLite — nenhuma estimativa.

Uso:
    python daily_report_generator.py           # gera relatório do dia
    python daily_report_generator.py --md      # força formato .md
    python daily_report_generator.py --json    # força formato .json
    python daily_report_generator.py --both    # gera ambos (padrão)
"""

import sys
import os
import json
import sqlite3
import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
# Se executado de 10_GITHUB, sobe um nível; se de raiz, usa direto
if _ROOT.name == "10_GITHUB":
    _ROOT = _ROOT.parent
elif not (_ROOT / "02_MEMORY").exists():
    # Tentar raiz relativa ao arquivo
    _ROOT = Path(__file__).resolve().parent
    if not (_ROOT / "02_MEMORY").exists():
        _ROOT = Path(__file__).resolve().parent.parent

DB_PATH  = _ROOT / "02_MEMORY" / "agente_x.db"
OUT_DIR  = _ROOT / "08_AUDITS" / "reports"
LOG_DIR  = _ROOT / "09_LOGS"

MODE_MD   = "--md"   in sys.argv or "--both" in sys.argv or len(sys.argv) == 1
MODE_JSON = "--json" in sys.argv or "--both" in sys.argv or len(sys.argv) == 1

TODAY     = datetime.date.today().isoformat()
NOW_TS    = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
NOW_ISO   = datetime.datetime.now().isoformat()


# ─────────────────────────────────────────────────────────────
#  Coleta de dados reais do banco
# ─────────────────────────────────────────────────────────────

def _db_connect():
    """Conecta ao DB com fallback para /tmp."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        # Teste de escrita não necessário — só leitura aqui
        return conn
    except Exception:
        import tempfile as _t
        fallback = _t.gettempdir() + "/agente_x_report.db"
        return sqlite3.connect(fallback)


def collect_data() -> dict:
    """Coleta todos os dados reais para o relatório."""
    data = {
        "timestamp": NOW_ISO,
        "date": TODAY,
        "db_available": DB_PATH.exists(),
        "missions": {},
        "queue": {},
        "finance": {},
        "logs": {},
        "knowledge": {},
        "providers": {},
        "backups": {},
    }

    if not DB_PATH.exists():
        return data

    try:
        conn = _db_connect()

        # ── Missões ─────────────────────────────────────────
        missions_rows = conn.execute(
            "SELECT code, title, status, started_at, ended_at FROM missions ORDER BY id"
        ).fetchall()
        all_missions = [dict(r) for r in missions_rows]
        data["missions"] = {
            "total": len(all_missions),
            "done":    sum(1 for m in all_missions if m["status"] == "DONE"),
            "pending": sum(1 for m in all_missions if m["status"] == "PENDING"),
            "running": sum(1 for m in all_missions if m["status"] == "RUNNING"),
            "failed":  sum(1 for m in all_missions if m["status"] == "FAILED"),
            "list":    all_missions[:20],  # primeiras 20 para o relatório
        }

        # ── Fila ─────────────────────────────────────────────
        queue_counts = {}
        for status in ("QUEUED", "RUNNING", "DONE", "FAILED", "CANCELLED"):
            cnt = conn.execute(
                "SELECT COUNT(*) FROM fila_execucao WHERE status=?", (status,)
            ).fetchone()[0]
            queue_counts[status.lower()] = cnt
        # Tasks concluídas hoje
        done_today = conn.execute(
            "SELECT COUNT(*) FROM fila_execucao WHERE status='DONE' AND finished_at LIKE ?",
            (f"{TODAY}%",)
        ).fetchone()[0]
        queue_counts["done_today"] = done_today
        # Stuck RUNNING
        one_hour_ago = (datetime.datetime.utcnow() - datetime.timedelta(hours=1)).isoformat()
        stuck = conn.execute(
            "SELECT COUNT(*) FROM fila_execucao WHERE status='RUNNING' AND started_at < ?",
            (one_hour_ago,)
        ).fetchone()[0]
        queue_counts["stuck_running"] = stuck
        data["queue"] = queue_counts

        # ── Finanças ─────────────────────────────────────────
        today_row = conn.execute(
            "SELECT SUM(custo_usd) FROM financeiro WHERE data=?", (TODAY,)
        ).fetchone()
        month = TODAY[:7]
        month_row = conn.execute(
            "SELECT SUM(custo_usd) FROM financeiro WHERE data LIKE ?", (f"{month}%",)
        ).fetchone()
        total_row = conn.execute("SELECT SUM(custo_usd) FROM financeiro").fetchone()
        # Modelo mais usado hoje
        top_model_row = conn.execute(
            "SELECT modelo, COUNT(*) as c FROM financeiro WHERE data=? GROUP BY modelo ORDER BY c DESC LIMIT 1",
            (TODAY,)
        ).fetchone()
        data["finance"] = {
            "today_usd":   round(today_row[0] or 0.0, 6),
            "month_usd":   round(month_row[0] or 0.0, 6),
            "total_usd":   round(total_row[0] or 0.0, 6),
            "top_model":   dict(top_model_row)["modelo"] if top_model_row else "N/A",
            "calls_today": conn.execute(
                "SELECT COUNT(*) FROM financeiro WHERE data=?", (TODAY,)
            ).fetchone()[0],
        }

        # ── Logs ─────────────────────────────────────────────
        total_logs = conn.execute("SELECT COUNT(*) FROM logs").fetchone()[0]
        errors_today = conn.execute(
            "SELECT COUNT(*) FROM logs WHERE level='ERROR' AND created_at LIKE ?",
            (f"{TODAY}%",)
        ).fetchone()[0]
        warns_today = conn.execute(
            "SELECT COUNT(*) FROM logs WHERE level='WARNING' AND created_at LIKE ?",
            (f"{TODAY}%",)
        ).fetchone()[0]
        # Últimos 5 erros
        recent_errors = [
            dict(r) for r in conn.execute(
                "SELECT level, source, message, created_at FROM logs WHERE level='ERROR' ORDER BY id DESC LIMIT 5"
            ).fetchall()
        ]
        data["logs"] = {
            "total": total_logs,
            "errors_today": errors_today,
            "warnings_today": warns_today,
            "recent_errors": recent_errors,
        }

        # ── Knowledge Base ────────────────────────────────────
        kb_total = conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
        kb_by_cat = [
            dict(r) for r in conn.execute(
                "SELECT category, COUNT(*) as count FROM knowledge GROUP BY category ORDER BY count DESC"
            ).fetchall()
        ]
        data["knowledge"] = {
            "total": kb_total,
            "by_category": kb_by_cat,
        }

        conn.close()
    except Exception as e:
        data["db_error"] = str(e)

    # ── Providers (do .env) ───────────────────────────────────
    env_path = _ROOT / ".env"
    placeholder = "SK-PLACEHOLDER"
    def _key_valid(k):
        return bool(k) and placeholder not in k and len(k) > 10

    env_vars = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env_vars[k.strip()] = v.strip()
    for k, v in env_vars.items():
        os.environ.setdefault(k, v)

    data["providers"] = {
        "deepseek": _key_valid(os.getenv("DEEPSEEK_API_KEY", "")),
        "claude":   _key_valid(os.getenv("CLAUDE_API_KEY", "")),
        "openai":   _key_valid(os.getenv("OPENAI_API_KEY", "")),
        "gemini":   _key_valid(os.getenv("GEMINI_API_KEY", "")),
    }
    data["providers"]["configured_count"] = sum(1 for v in data["providers"].values() if v is True)

    # ── Backups ───────────────────────────────────────────────
    backup_dir = _ROOT / "13_BACKUPS_DIARIOS"
    if backup_dir.exists():
        backups = sorted([d.name for d in backup_dir.iterdir() if d.is_dir() and d.name.startswith("backup_")])
        data["backups"] = {
            "count": len(backups),
            "latest": backups[-1] if backups else None,
            "list": backups[-5:],  # últimos 5
        }
    else:
        data["backups"] = {"count": 0, "latest": None, "list": []}

    return data


# ─────────────────────────────────────────────────────────────
#  Geração do Markdown
# ─────────────────────────────────────────────────────────────

def generate_markdown(d: dict) -> str:
    m   = d["missions"]
    q   = d["queue"]
    fin = d["finance"]
    lg  = d["logs"]
    kb  = d["knowledge"]
    pv  = d["providers"]
    bk  = d["backups"]

    pv_list = []
    for p in ("deepseek", "claude", "openai", "gemini"):
        pv_list.append(f"{'OK' if pv.get(p) else '--'} {p.upper()}")

    mission_lines = ""
    for ms in m.get("list", []):
        icon = {"DONE": "✅", "RUNNING": "🔄", "PENDING": "⏳", "FAILED": "❌"}.get(ms["status"], "◻")
        mission_lines += f"| {icon} | `{ms['code']}` | {ms['title']} | {ms['status']} |\n"

    errors_section = ""
    if lg.get("recent_errors"):
        errors_section = "\n## 🔴 Últimos Erros\n\n```\n"
        for e in lg["recent_errors"]:
            errors_section += f"[{e.get('created_at','')}] [{e.get('source','')}] {e.get('message','')}\n"
        errors_section += "```\n"

    kb_cats = ""
    for cat in kb.get("by_category", []):
        kb_cats += f"  - `{cat['category']}`: {cat['count']} registros\n"

    report = f"""# AGENTE-X — Relatório Diário
**Data:** {d['date']}  |  **Gerado:** {NOW_TS}

---

## 📊 Resumo Executivo

| Indicador | Valor |
|-----------|-------|
| Missões concluídas | {m.get('done', 0)} / {m.get('total', 0)} |
| Tarefas na fila | {q.get('queued', 0)} aguardando |
| Tarefas concluídas hoje | {q.get('done_today', 0)} |
| Gasto LLM hoje | ${fin.get('today_usd', 0):.6f} |
| Gasto no mês | ${fin.get('month_usd', 0):.6f} |
| Erros hoje | {lg.get('errors_today', 0)} |
| Knowledge Base | {kb.get('total', 0)} registros |
| Providers ativos | {pv.get('configured_count', 0)}/4 |
| Último backup | {bk.get('latest', 'N/A')} |

---

## 🎯 Missões

| | Código | Título | Status |
|---|--------|--------|--------|
{mission_lines}
---

## ⚙️ Fila de Execução

| Status | Quantidade |
|--------|-----------|
| QUEUED | {q.get('queued', 0)} |
| RUNNING | {q.get('running', 0)} |
| DONE | {q.get('done', 0)} |
| FAILED | {q.get('failed', 0)} |
| CANCELLED | {q.get('cancelled', 0)} |
| Stuck >1h | {q.get('stuck_running', 0)} |

---

## 💰 Finanças LLM

- **Hoje:** ${fin.get('today_usd', 0):.6f}
- **Mês:** ${fin.get('month_usd', 0):.6f}
- **Total histórico:** ${fin.get('total_usd', 0):.6f}
- **Chamadas hoje:** {fin.get('calls_today', 0)}
- **Modelo mais usado hoje:** `{fin.get('top_model', 'N/A')}`

---

## 🧠 Knowledge Base

- **Total:** {kb.get('total', 0)} registros
{kb_cats}
---

## 🔌 Providers Configurados

```
{chr(10).join(pv_list)}
```

---

## 💾 Backups

- **Total de backups:** {bk.get('count', 0)}
- **Último backup:** {bk.get('latest', 'Nenhum')}
- **Histórico recente:** {', '.join(bk.get('list', []))}
{errors_section}
---
*Gerado automaticamente pelo AGENTE-X Daily Report Generator | Zero Ghost*
"""
    return report


# ─────────────────────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────────────────────

def generate_daily_report() -> dict:
    """
    Função principal — chamável pelo SaveManager.
    Retorna dict com os paths dos arquivos gerados.
    """
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = collect_data()
    output = {"json_path": None, "md_path": None, "ok": True}

    if MODE_JSON or True:  # sempre gera JSON para machine-readable
        json_path = OUT_DIR / f"relatorio_{TODAY}.json"
        json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        output["json_path"] = str(json_path)

    if MODE_MD or True:  # sempre gera MD para leitura humana
        md = generate_markdown(data)
        md_path = OUT_DIR / f"RELATORIO_{TODAY}.md"
        md_path.write_text(md, encoding="utf-8")
        output["md_path"] = str(md_path)

    # Log no banco
    if DB_PATH.exists():
        try:
            conn = _db_connect()
            conn.execute(
                "INSERT INTO logs (level, source, message) VALUES ('INFO', 'DailyReport', ?)",
                (f"Relatório diário gerado: {output['md_path']}",)
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

    return output


if __name__ == "__main__":
    result = generate_daily_report()
    if result["md_path"]:
        print(f"[OK] Relatorio MD  : {result['md_path']}")
    if result["json_path"]:
        print(f"[OK] Relatorio JSON: {result['json_path']}")
