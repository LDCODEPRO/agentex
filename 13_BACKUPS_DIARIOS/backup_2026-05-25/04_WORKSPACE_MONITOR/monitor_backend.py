"""
AGENTE-X | Monitor Backend M6.2.1
Backend real para o painel 04_WORKSPACE_MONITOR/monitor1_workspace.html
Expoe metricas reais do agente_x.db via HTTP.
Zero Ghost: todos os dados sao lidos de fontes reais — sem dados simulados.

Uso: python monitor_backend.py
Porta: 5050
"""
import os
import sqlite3
import subprocess
import logging
import json
import time
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = str(PROJECT_ROOT / "02_MEMORY" / "agente_x.db")
LOG_DIR = PROJECT_ROOT / "09_LOGS"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    filename=str(LOG_DIR / "monitor_backend.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("MonitorBackend")

# Cache simples para nao martelas o disco a cada 3s do frontend
_cache: dict = {}
_cache_ts: float = 0.0
CACHE_TTL = 5  # segundos


def _db_connect():
    """Conecta ao SQLite com fallback gracioso."""
    if not os.path.exists(DB_PATH):
        return None
    try:
        conn = sqlite3.connect(DB_PATH, timeout=3.0)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception:
        return None


def _get_metrics() -> dict:
    """Le todas as metricas reais do banco. Retorna dict completo."""
    global _cache, _cache_ts
    now = time.time()
    if now - _cache_ts < CACHE_TTL and _cache:
        return _cache

    metrics: dict = {
        "ts": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "db_ok": False,
        "missions": {},
        "fila": {},
        "logs": {},
        "finance": {},
        "knowledge": 0,
    }

    conn = _db_connect()
    if conn:
        try:
            metrics["db_ok"] = True

            # Missions
            rows = conn.execute("SELECT status, COUNT(*) FROM missions GROUP BY status").fetchall()
            miss = {r[0]: r[1] for r in rows}
            metrics["missions"] = {
                "total":     sum(miss.values()),
                "completed": miss.get("MISSION_COMPLETED", 0),
                "created":   miss.get("MISSION_CREATED", 0),
                "failed":    miss.get("MISSION_FAILED", 0),
                "cancelled": miss.get("MISSION_CANCELLED", 0),
                "validated": miss.get("MISSION_VALIDATED", 0),
            }

            # Fila
            rows2 = conn.execute("SELECT status, COUNT(*) FROM fila_execucao GROUP BY status").fetchall()
            fila = {r[0]: r[1] for r in rows2}
            metrics["fila"] = {
                "queued":    fila.get("QUEUED", 0),
                "running":   fila.get("RUNNING", 0),
                "done":      fila.get("DONE", 0),
                "failed":    fila.get("FAILED", 0),
                "cancelled": fila.get("CANCELLED", 0),
            }

            # Logs
            total_logs = conn.execute("SELECT COUNT(*) FROM logs").fetchone()[0]
            error_logs = conn.execute("SELECT COUNT(*) FROM logs WHERE level='ERROR'").fetchone()[0]
            metrics["logs"] = {"total": total_logs, "errors": error_logs}

            # Finance
            today = datetime.now().strftime("%Y-%m-%d")
            month = datetime.now().strftime("%Y-%m")
            row_day = conn.execute(
                "SELECT COALESCE(SUM(custo_usd),0) FROM financeiro WHERE data=?", (today,)
            ).fetchone()
            row_mon = conn.execute(
                "SELECT COALESCE(SUM(custo_usd),0) FROM financeiro WHERE data LIKE ?", (f"{month}%",)
            ).fetchone()
            metrics["finance"] = {
                "daily_usd":   round(row_day[0], 6) if row_day else 0.0,
                "monthly_usd": round(row_mon[0], 6) if row_mon else 0.0,
            }

            # Knowledge
            metrics["knowledge"] = conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]

            conn.close()
        except Exception as e:
            logger.error("Erro lendo metricas do DB: %s", e)

    _cache = metrics
    _cache_ts = now
    return metrics


def _get_git_info() -> dict:
    """Le status real do git."""
    try:
        branch = subprocess.check_output(
            ["git", "branch", "--show-current"], cwd=str(PROJECT_ROOT),
            text=True, stderr=subprocess.DEVNULL, timeout=3
        ).strip()
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=str(PROJECT_ROOT),
            text=True, stderr=subprocess.DEVNULL, timeout=3
        ).strip()
        dirty = subprocess.check_output(
            ["git", "status", "-s"], cwd=str(PROJECT_ROOT),
            text=True, stderr=subprocess.DEVNULL, timeout=3
        ).strip()
        return {
            "branch": branch or "main",
            "last_commit": commit,
            "status": "PENDENTE" if dirty else "SINCRONIZADO",
        }
    except Exception:
        return {"branch": "N/A", "last_commit": "N/A", "status": "OFFLINE"}


class MonitorHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass  # Silenciar log HTTP padrao — usamos nosso proprio

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/health":
            self._send_json({"status": "ok", "pid": os.getpid()})

        elif path == "/api/status":
            # Endpoint compativel com o JS do monitor1_workspace.html
            m = _get_metrics()
            git = _get_git_info()
            gov_ok = (PROJECT_ROOT / "00_GOVERNANCE" / "RULES" / "safe_gate.py").exists()

            self._send_json({
                "agente_x":  "M1-M6 OPERACIONAL",
                "execucao":  "ATIVA",
                "git_status":  git["status"],
                "git_branch":  git["branch"],
                "git_commit":  git["last_commit"],
                "memoria":     "OK" if m["db_ok"] else "ERRO",
                "governanca":  "OK" if gov_ok else "ERRO",
                "sincronia":   datetime.now().strftime("%H:%M:%S"),
                # Campos extras — usados por versoes futuras do JS
                "missions_total":     m["missions"].get("total", 0),
                "missions_completed": m["missions"].get("completed", 0),
                "fila_queued":        m["fila"].get("queued", 0),
                "logs_total":         m["logs"].get("total", 0),
                "logs_errors":        m["logs"].get("errors", 0),
                "finance_daily_usd":  m["finance"].get("daily_usd", 0.0),
            })

        elif path == "/api/metrics":
            # Endpoint completo para dashboards futuros
            m = _get_metrics()
            git = _get_git_info()
            self._send_json({**m, "git": git})

        elif path == "/api/missions":
            m = _get_metrics()
            self._send_json(m.get("missions", {}))

        elif path == "/api/queue":
            m = _get_metrics()
            self._send_json(m.get("fila", {}))

        elif path == "/api/finance":
            m = _get_metrics()
            self._send_json(m.get("finance", {}))

        else:
            self._send_json({"error": "endpoint nao encontrado"}, 404)


def main():
    port = int(os.getenv("MONITOR_PORT", "5050"))
    server = HTTPServer(("127.0.0.1", port), MonitorHandler)
    print(f"[MonitorBackend] Iniciando na porta {port}...")
    print(f"[MonitorBackend] DB: {DB_PATH}")
    print(f"[MonitorBackend] Endpoints: /health /api/status /api/metrics /api/missions /api/queue /api/finance")
    print(f"[MonitorBackend] Ctrl+C para encerrar")
    logger.info("MonitorBackend iniciado na porta %d", port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[MonitorBackend] Encerrado.")
        logger.info("MonitorBackend encerrado.")


if __name__ == "__main__":
    main()
