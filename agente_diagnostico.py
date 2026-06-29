"""
AGENTE-X | Diagnóstico Completo
Verifica todos os módulos, DB, providers, backups, fila e gera relatório JSON.
Princípio Zero Ghost: todos os dados são REAIS — nenhum mock ou simulação.

Uso:
    python agente_diagnostico.py            # relatório completo
    python agente_diagnostico.py --quiet    # só JSON, sem output
"""

import ast
import sys
import os
import json
import sqlite3
import datetime
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
QUIET = "--quiet" in sys.argv

SEP = "=" * 60


def log(msg: str, level: str = "INFO"):
    if not QUIET:
        tag = {"INFO": "  ", "OK": "[OK] ", "WARN": "[AV] ", "ERR": "[!!] ", "HEAD": ""}
        print(f"{tag.get(level, '')}{msg}")


MODULES = [
    "00_GOVERNANCE/RULES/safe_gate.py",
    "00_GOVERNANCE/RULES/risk_engine.py",
    "01_CORE/orchestrator/llm_router.py",
    "01_CORE/orchestrator/tool_registry.py",
    "01_CORE/orchestrator/react_engine.py",
    "01_CORE/orchestrator/task_classifier.py",
    "01_CORE/orchestrator/learning_loop.py",
    "01_CORE/tools/base_tool.py",
    "01_CORE/tools/file_tool.py",
    "01_CORE/tools/shell_tool.py",
    "01_CORE/tools/memory_tool.py",
    "01_CORE/tools/web_tool.py",
    "01_CORE/finance/finance_engine.py",
    "01_CORE/validation/hallucination_guard.py",
    "01_CORE/validation/trace_context.py",
    "01_CORE/validation/anti_loop_guard.py",
    "02_MEMORY/long_term/db_init.py",
    "02_MEMORY/long_term/memory_manager.py",
    "02_MEMORY/vector_memory/chroma_manager.py",
    "02_MEMORY/short_term/context_manager.py",
    "03_RUNTIME/maestro.py",
    "04_SKILLS/skill_manager.py",
    "04_SKILLS/hermes_core.py",
    "04_SKILLS/hermes_knowledge_seeder.py",
    "06_CONTAINERS/whatsapp/whatsapp_agent.py",
    "10_GITHUB/save_manager.py",
    "10_GITHUB/daily_report_generator.py",
    "01_CORE/mission_engine/mission_brain.py",
    "01_CORE/mission_engine/mission_engine.py",
    "01_CORE/mission_engine/mission_executor.py",
    "01_CORE/mission_engine/mission_planner.py",
    "01_CORE/mission_engine/mission_templates.py",
    "01_CORE/mission_engine/mission_validator.py",
    "01_CORE/mission_engine/rollback_engine.py",
    "agente_x.py",
    "setup_agente_x.py",
    "agente_diagnostico.py",
    # M8: Health & Observability
    "05_HEALTH/health_monitor.py",
    "05_HEALTH/performance_tracker.py",
    "05_HEALTH/auto_tuner.py",
]

EXPECTED_TABLES = [
    "missions", "sessions", "logs", "knowledge",
    "fila_execucao", "financeiro", "llm_usage_ledger", "rate_limit_stats",
]
PLACEHOLDER = "SK-PLACEHOLDER"


def _key_valid(k: str) -> bool:
    return bool(k) and PLACEHOLDER not in k and len(k) > 10


def check_modules() -> dict:
    log("\n[1/6] MODULOS PYTHON", "HEAD")
    results = {"ok": [], "missing": [], "syntax_error": []}
    for rel in MODULES:
        path = ROOT / rel
        if not path.exists():
            log(f"AUSENTE  {rel}", "WARN")
            results["missing"].append(rel)
            continue
        try:
            ast.parse(path.read_text(encoding="utf-8", errors="replace"))
            log(f"OK       {rel}", "OK")
            results["ok"].append(rel)
        except SyntaxError as e:
            log(f"SINTAXE  {rel}: {e}", "ERR")
            results["syntax_error"].append({"file": rel, "error": str(e)})
    return results


def check_database() -> dict:
    log("\n[2/6] BANCO DE DADOS SQLITE", "HEAD")
    db_path = ROOT / "02_MEMORY" / "agente_x.db"
    result = {
        "db_path": str(db_path),
        "exists": db_path.exists(),
        "size_kb": 0,
        "tables": {},
        "missing_tables": [],
        "queue_health": {},
        "finance_today": 0.0,
    }
    if not db_path.exists():
        log(f"DB NAO ENCONTRADO: {db_path}", "ERR")
        return result

    result["size_kb"] = round(db_path.stat().st_size / 1024, 1)
    log(f"DB: {db_path}  ({result['size_kb']} KB)", "OK")

    try:
        conn = sqlite3.connect(str(db_path))
        existing = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()]

        for t in EXPECTED_TABLES:
            if t not in existing:
                result["missing_tables"].append(t)
                log(f"TABELA AUSENTE: {t}", "ERR")
            else:
                cnt = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                result["tables"][t] = cnt
                log(f"  {t}: {cnt} rows", "INFO")

        if "fila_execucao" in existing:
            for status in ("QUEUED", "RUNNING", "DONE", "FAILED", "CANCELLED"):
                cnt = conn.execute(
                    "SELECT COUNT(*) FROM fila_execucao WHERE status=?", (status,)
                ).fetchone()[0]
                result["queue_health"][status] = cnt
            log(f"  Fila: {result['queue_health']}", "INFO")

            one_hour_ago = (datetime.datetime.utcnow() - datetime.timedelta(hours=1)).isoformat()
            stuck = conn.execute(
                "SELECT COUNT(*) FROM fila_execucao WHERE status='RUNNING' AND started_at < ?",
                (one_hour_ago,)
            ).fetchone()[0]
            result["queue_health"]["stuck_running"] = stuck
            if stuck > 0:
                log(f"  RUNNING presos >1h: {stuck}", "WARN")

        if "financeiro" in existing:
            today = datetime.date.today().isoformat()
            row = conn.execute(
                "SELECT SUM(custo_usd) FROM financeiro WHERE data=?", (today,)
            ).fetchone()
            result["finance_today"] = round(row[0] or 0.0, 6)
            log(f"  Gasto hoje: ${result['finance_today']:.6f}", "INFO")

        conn.close()
    except Exception as e:
        log(f"Erro ao ler DB: {e}", "ERR")
        result["db_error"] = str(e)

    return result


def check_providers() -> dict:
    log("\n[3/6] PROVIDERS LLM", "HEAD")
    env_path = ROOT / ".env"
    env_vars: dict = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env_vars[k.strip()] = v.strip()
    for k, v in env_vars.items():
        if k not in os.environ:
            os.environ[k] = v

    result = {
        "env_exists":  env_path.exists(),
        "deepseek": _key_valid(os.getenv("DEEPSEEK_API_KEY", "")),
        "claude":   _key_valid(os.getenv("CLAUDE_API_KEY", "")),
        "openai":   _key_valid(os.getenv("OPENAI_API_KEY", "")),
        "gemini":   _key_valid(os.getenv("GEMINI_API_KEY", "")),
        "ollama_host": os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        "ollama_alive": False,
    }
    try:
        import urllib.request
        req = urllib.request.urlopen(result["ollama_host"] + "/api/tags", timeout=2)
        result["ollama_alive"] = req.status == 200
    except Exception:
        pass

    for prov in ("deepseek", "claude", "openai", "gemini"):
        status = "CONFIGURADO" if result[prov] else "NAO CONFIGURADO"
        lvl = "OK" if result[prov] else "WARN"
        log(f"  {prov.upper()}: {status}", lvl)
    log(f"  OLLAMA: {'ONLINE' if result['ollama_alive'] else 'OFFLINE'}", "INFO")
    result["configured_count"] = sum(1 for p in ("deepseek","claude","openai","gemini") if result[p])
    log(f"  Providers configurados: {result['configured_count']}/4", "INFO")
    return result


def check_backups() -> dict:
    log("\n[4/6] BACKUPS DIARIOS", "HEAD")
    backup_dir = ROOT / "13_BACKUPS_DIARIOS"
    result = {
        "backup_dir_exists": backup_dir.exists(),
        "backups_found": [],
        "latest_backup": None,
        "days_since_backup": None,
        "bat_exists": (backup_dir / "BACKUP_DIARIO.bat").exists() if backup_dir.exists() else False,
    }
    if not backup_dir.exists():
        log("Diretorio de backups nao encontrado", "ERR")
        return result

    backups = sorted([
        d.name for d in backup_dir.iterdir()
        if d.is_dir() and d.name.startswith("backup_")
    ])
    result["backups_found"] = backups
    log(f"  Backups encontrados: {len(backups)}", "INFO")

    if backups:
        latest = backups[-1]
        result["latest_backup"] = latest
        try:
            date_str = latest.replace("backup_", "")
            backup_date = datetime.date.fromisoformat(date_str)
            result["days_since_backup"] = (datetime.date.today() - backup_date).days
            lvl = "OK" if result["days_since_backup"] <= 1 else "WARN"
            log(f"  Ultimo backup: {latest} ({result['days_since_backup']} dias atras)", lvl)
        except Exception:
            log(f"  Ultimo backup: {latest}", "INFO")
    else:
        log("  Nenhum backup encontrado", "ERR")

    if result["bat_exists"]:
        log("  BACKUP_DIARIO.bat: PRESENTE", "OK")
    else:
        log("  BACKUP_DIARIO.bat: AUSENTE", "WARN")
    return result


def check_environment() -> dict:
    log("\n[5/6] AMBIENTE E DEPENDENCIAS", "HEAD")
    result = {
        "python_version": sys.version.split()[0],
        "platform": sys.platform,
        "root": str(ROOT),
        "deps": {},
        "env_exists":  (ROOT / ".env").exists(),
        "soul_exists": (ROOT / "12_CONFIG" / "SOUL.md").exists(),
        "agents_exists": (ROOT / "12_CONFIG" / "AGENTS.md").exists(),
    }
    log(f"  Python: {result['python_version']}", "INFO")
    for dep in ["requests", "dotenv", "sqlite3", "chromadb", "fastapi", "uvicorn"]:
        try:
            __import__(dep)
            result["deps"][dep] = "OK"
            log(f"  {dep}: OK", "OK")
        except ImportError:
            result["deps"][dep] = "AUSENTE"
            log(f"  {dep}: AUSENTE", "WARN")

    log(f"  .env: {'PRESENTE' if result['env_exists'] else 'AUSENTE'}", "OK" if result["env_exists"] else "ERR")
    log(f"  SOUL.md: {'PRESENTE' if result['soul_exists'] else 'AUSENTE'}", "OK" if result["soul_exists"] else "ERR")
    return result


def compute_score(modules, db, providers, backups, env) -> dict:
    issues = []
    score = 100
    missing_m = len(modules["missing"])
    syntax_m  = len(modules["syntax_error"])
    score -= missing_m * 3
    score -= syntax_m * 5
    if missing_m: issues.append(f"{missing_m} modulos ausentes")
    if syntax_m:  issues.append(f"{syntax_m} modulos com erro de sintaxe")
    if not db["exists"]:
        score -= 20
        issues.append("Banco de dados ausente")
    missing_tables = len(db.get("missing_tables", []))
    score -= missing_tables * 4
    if missing_tables: issues.append(f"{missing_tables} tabelas ausentes no DB")
    stuck = db.get("queue_health", {}).get("stuck_running", 0)
    if stuck > 0:
        score -= min(10, stuck)
        issues.append(f"{stuck} missions RUNNING presas >1h")
    if providers["configured_count"] == 0 and not providers["ollama_alive"]:
        score -= 20
        issues.append("Nenhum provider LLM disponivel")
    elif providers["configured_count"] < 2:
        score -= 5
        issues.append("Menos de 2 providers configurados")
    days = backups.get("days_since_backup")
    if days is None:
        score -= 10
        issues.append("Nenhum backup encontrado")
    elif days > 1:
        score -= 5
        issues.append(f"Backup desatualizado: {days} dias")
    if not env.get("env_exists"):
        score -= 10
        issues.append(".env ausente")
    if not env.get("soul_exists"):
        score -= 5
        issues.append("SOUL.md ausente")
    score = max(0, score)
    if score >= 90: status = "EXCELENTE"
    elif score >= 75: status = "BOM"
    elif score >= 60: status = "ATENCAO"
    else: status = "CRITICO"
    return {
        "score": score,
        "status": status,
        "issues": issues,
        "modules_ok": len(modules["ok"]),
        "modules_total": len(MODULES),
    }


def save_report(report: dict) -> Path:
    reports_dir = ROOT / "08_AUDITS" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    out = reports_dir / f"diagnostico_{today}.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def main():
    started = time.time()
    if not QUIET:
        print(SEP)
        print("  AGENTE-X | Diagnostico Completo")
        print(f"  {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(SEP)

    modules   = check_modules()
    db        = check_database()
    providers = check_providers()
    backups   = check_backups()
    env       = check_environment()
    score     = compute_score(modules, db, providers, backups, env)
    elapsed   = round(time.time() - started, 2)

    report = {
        "timestamp":   datetime.datetime.now().isoformat(),
        "elapsed_s":   elapsed,
        "score":       score,
        "modules":     modules,
        "database":    db,
        "providers":   providers,
        "backups":     backups,
        "environment": env,
    }

    out_path = save_report(report)

    if not QUIET:
        print(f"\n{SEP}")
        print(f"  SCORE FINAL: {score['score']}/100 -- {score['status']}")
        if score["issues"]:
            print(f"  Problemas detectados ({len(score['issues'])}):")
            for iss in score["issues"]:
                print(f"    [!] {iss}")
        else:
            print("  Nenhum problema critico detectado.")
        print(f"\n  Relatorio: {out_path}")
        print(f"  Tempo total: {elapsed}s")
        print(SEP)

    return 0 if score["score"] >= 60 else 1


if __name__ == "__main__":
    sys.exit(main())
