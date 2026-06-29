"""
AGENTE-X | Performance Tracker (M8)
Rastreia metricas reais de execucao por missao:
  - Tokens consumidos (entrada + saida)
  - Custo USD real (via tabela financeiro)
  - Tempo de execucao (segundos)
  - Taxa de sucesso (DONE vs FAILED)
  - Provedor LLM mais usado

Zero Ghost: todos os dados sao lidos do SQLite — nenhuma estimativa.

Uso:
    python performance_tracker.py           # metricas do dia
    python performance_tracker.py --all     # metricas historicas
    python performance_tracker.py --mission M8  # missao especifica
"""
import sys
import sqlite3
import datetime
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

DB_PATH  = _ROOT / "02_MEMORY" / "agente_x.db"
OUT_DIR  = _ROOT / "08_AUDITS" / "performance"
TODAY    = datetime.date.today().isoformat()
MONTH    = TODAY[:7]


def _connect():
    if not DB_PATH.exists():
        raise FileNotFoundError("DB nao encontrado: " + str(DB_PATH))
    conn = sqlite3.connect(str(DB_PATH), timeout=5.0)
    conn.row_factory = sqlite3.Row
    return conn


def collect_mission_metrics(mission_code: str = None) -> dict:
    """
    Coleta metricas reais de missoes do banco.
    Se mission_code fornecido, filtra para essa missao.
    """
    conn = _connect()
    metrics = {}

    # ── Missoes: status geral ─────────────────────────────────
    where = ""
    params = []
    if mission_code:
        where = "WHERE code=?"
        params = [mission_code]

    missions = [dict(r) for r in conn.execute(
        "SELECT code, title, status, started_at, ended_at, retry_count FROM missions " + where,
        params
    ).fetchall()]

    total        = len(missions)
    completed    = sum(1 for m in missions if "COMPLETED" in (m["status"] or ""))
    failed       = sum(1 for m in missions if "FAILED" in (m["status"] or ""))
    running      = sum(1 for m in missions if "RUNNING" in (m["status"] or ""))
    success_rate = round((completed / total * 100) if total > 0 else 0, 1)

    metrics["missions"] = {
        "total": total,
        "completed": completed,
        "failed": failed,
        "running": running,
        "success_rate_pct": success_rate,
    }

    # ── Fila: throughput hoje ─────────────────────────────────
    done_today = conn.execute(
        "SELECT COUNT(*) FROM fila_execucao WHERE status='DONE' AND finished_at LIKE ?",
        (TODAY + "%",)
    ).fetchone()[0]

    fail_today = conn.execute(
        "SELECT COUNT(*) FROM fila_execucao WHERE status='FAILED' AND finished_at LIKE ?",
        (TODAY + "%",)
    ).fetchone()[0]

    metrics["queue_today"] = {
        "done": done_today,
        "failed": fail_today,
        "throughput_rate": round(done_today / (done_today + fail_today) * 100, 1) if (done_today + fail_today) > 0 else 0,
    }

    # ── Financeiro: consumo real ──────────────────────────────
    today_row   = conn.execute("SELECT SUM(custo_usd), SUM(tokens_input), SUM(tokens_output) FROM financeiro WHERE data=?", (TODAY,)).fetchone()
    month_row   = conn.execute("SELECT SUM(custo_usd), SUM(tokens_input), SUM(tokens_output) FROM financeiro WHERE data LIKE ?", (MONTH + "%",)).fetchone()
    total_row   = conn.execute("SELECT SUM(custo_usd), SUM(tokens_input), SUM(tokens_output) FROM financeiro").fetchone()
    calls_today = conn.execute("SELECT COUNT(*) FROM financeiro WHERE data=?", (TODAY,)).fetchone()[0]

    # Modelo mais caro hoje
    top_cost = conn.execute(
        "SELECT modelo, SUM(custo_usd) as total FROM financeiro WHERE data=? GROUP BY modelo ORDER BY total DESC LIMIT 1",
        (TODAY,)
    ).fetchone()

    # Provedor mais usado historico
    top_provider = conn.execute(
        "SELECT modelo, COUNT(*) as c FROM financeiro GROUP BY modelo ORDER BY c DESC LIMIT 1"
    ).fetchone()

    metrics["finance"] = {
        "today_usd":    round(today_row[0] or 0.0, 6),
        "today_tokens_in":  int(today_row[1] or 0),
        "today_tokens_out": int(today_row[2] or 0),
        "month_usd":    round(month_row[0] or 0.0, 6),
        "total_usd":    round(total_row[0] or 0.0, 6),
        "calls_today":  calls_today,
        "top_model_today":   top_cost["modelo"] if top_cost else "N/A",
        "top_provider_ever": top_provider["modelo"] if top_provider else "N/A",
        "avg_cost_per_call_today": round((today_row[0] or 0.0) / calls_today, 6) if calls_today > 0 else 0.0,
    }

    # ── Erros: taxa de erro ───────────────────────────────────
    errors_today = conn.execute(
        "SELECT COUNT(*) FROM logs WHERE level='ERROR' AND created_at LIKE ?",
        (TODAY + "%",)
    ).fetchone()[0]
    total_logs_today = conn.execute(
        "SELECT COUNT(*) FROM logs WHERE created_at LIKE ?", (TODAY + "%",)
    ).fetchone()[0]

    metrics["reliability"] = {
        "errors_today": errors_today,
        "error_rate_pct": round(errors_today / total_logs_today * 100, 2) if total_logs_today > 0 else 0.0,
        "total_events_today": total_logs_today,
    }

    # ── Knowledge base: crescimento ──────────────────────────
    kb_total = conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
    kb_rules  = conn.execute("SELECT COUNT(*) FROM knowledge WHERE category='RULE'").fetchone()[0]
    kb_learned = conn.execute("SELECT COUNT(*) FROM knowledge WHERE category LIKE 'LEARNED%'").fetchone()[0]

    metrics["knowledge"] = {
        "total": kb_total,
        "governance_rules": kb_rules,
        "learned_facts": kb_learned,
    }

    conn.close()
    return metrics


def generate_report(metrics: dict) -> str:
    m  = metrics["missions"]
    q  = metrics["queue_today"]
    f  = metrics["finance"]
    r  = metrics["reliability"]
    kb = metrics["knowledge"]

    return (
        "# AGENTE-X — Performance Report\n"
        f"**Data:** {TODAY}  |  **Gerado:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        "---\n\n"
        "## Missoes\n\n"
        f"| Metrica | Valor |\n|---------|-------|\n"
        f"| Total missoes | {m['total']} |\n"
        f"| Concluidas | {m['completed']} |\n"
        f"| Falhas | {m['failed']} |\n"
        f"| Em execucao | {m['running']} |\n"
        f"| Taxa de sucesso | {m['success_rate_pct']}% |\n\n"
        "## Fila (hoje)\n\n"
        f"| Metrica | Valor |\n|---------|-------|\n"
        f"| Tarefas concluidas | {q['done']} |\n"
        f"| Tarefas com falha | {q['failed']} |\n"
        f"| Throughput rate | {q['throughput_rate']}% |\n\n"
        "## Financeiro\n\n"
        f"| Metrica | Valor |\n|---------|-------|\n"
        f"| Gasto hoje | ${f['today_usd']:.6f} |\n"
        f"| Tokens entrada hoje | {f['today_tokens_in']:,} |\n"
        f"| Tokens saida hoje | {f['today_tokens_out']:,} |\n"
        f"| Chamadas LLM hoje | {f['calls_today']} |\n"
        f"| Custo medio/chamada | ${f['avg_cost_per_call_today']:.6f} |\n"
        f"| Gasto no mes | ${f['month_usd']:.6f} |\n"
        f"| Gasto total historico | ${f['total_usd']:.6f} |\n"
        f"| Modelo mais caro hoje | `{f['top_model_today']}` |\n"
        f"| Provider mais usado | `{f['top_provider_ever']}` |\n\n"
        "## Confiabilidade\n\n"
        f"| Metrica | Valor |\n|---------|-------|\n"
        f"| Erros hoje | {r['errors_today']} |\n"
        f"| Taxa de erro | {r['error_rate_pct']}% |\n"
        f"| Total eventos hoje | {r['total_events_today']} |\n\n"
        "## Knowledge Base\n\n"
        f"| Metrica | Valor |\n|---------|-------|\n"
        f"| Total registros | {kb['total']} |\n"
        f"| Regras de governanca | {kb['governance_rules']} |\n"
        f"| Fatos aprendidos | {kb['learned_facts']} |\n\n"
        "---\n"
        "*Gerado pelo AGENTE-X Performance Tracker M8 | Zero Ghost*\n"
    )


def run(mission_code: str = None) -> dict:
    """Ponto de entrada principal. Retorna metricas e salva relatorio."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    metrics = collect_mission_metrics(mission_code)

    # Salvar JSON
    json_path = OUT_DIR / f"perf_{TODAY}.json"
    json_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")

    # Salvar MD
    md = generate_report(metrics)
    md_path = OUT_DIR / f"PERF_{TODAY}.md"
    md_path.write_text(md, encoding="utf-8")

    return metrics


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="AGENTE-X Performance Tracker M8")
    parser.add_argument("--mission", type=str, default=None, help="Filtrar por missao especifica")
    parser.add_argument("--all", action="store_true", help="Historico completo")
    args = parser.parse_args()

    print("=" * 60)
    print("  AGENTE-X | Performance Tracker M8")
    print(f"  {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    metrics = run(args.mission)
    fin = metrics["finance"]
    mis = metrics["missions"]
    rel = metrics["reliability"]

    print(f"\n  Missoes: {mis['total']} total | {mis['completed']} OK | {mis['failed']} FAILED | {mis['success_rate_pct']}% sucesso")
    print(f"  Financeiro: ${fin['today_usd']:.6f} hoje | {fin['calls_today']} chamadas LLM")
    print(f"  Confiabilidade: {rel['errors_today']} erros hoje | {rel['error_rate_pct']}% taxa de erro")
    print(f"  Knowledge: {metrics['knowledge']['total']} registros")
    print(f"\n  Relatorio salvo em: 08_AUDITS/performance/PERF_{TODAY}.md")
    print("=" * 60)
