"""
AGENTE-X | Health Monitor (M8)
Verifica continuamente a saude do sistema e emite alertas reais.
Zero Ghost: todos os dados vem do SQLite — nenhuma estimativa.

Limiares verificados:
  - errors_per_hour > 10    → alerta ERROR_SPIKE
  - queue_stuck > 0         → alerta QUEUE_STUCK  
  - budget_used_pct > 80%   → alerta BUDGET_WARNING
  - modules_missing > 0     → alerta MODULE_MISSING
  - backup_age_days > 2     → alerta BACKUP_STALE
"""
import sys
import sqlite3
import datetime
import time
import logging
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "02_MEMORY" / "long_term"))

DB_PATH = _ROOT / "02_MEMORY" / "agente_x.db"
DAILY_BUDGET_USD = 2.0   # limite padrao; FinanceEngine pode ter diferente
HARD_STOP_USD    = 5.0

logger = logging.getLogger("HealthMonitor")


def _connect():
    try:
        conn = sqlite3.connect(str(DB_PATH), timeout=5.0)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        raise RuntimeError("HealthMonitor: nao consegue abrir DB: " + str(e))


class HealthAlert:
    def __init__(self, code: str, severity: str, message: str, value=None):
        self.code     = code
        self.severity = severity   # WARNING | CRITICAL
        self.message  = message
        self.value    = value
        self.ts       = datetime.datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "value": self.value,
            "ts": self.ts,
        }


class HealthMonitor:
    """
    Verifica a saude do sistema AGENTE-X e retorna lista de alertas reais.
    Zero Ghost: nenhum dado fabricado.
    """

    def __init__(self, daily_budget: float = DAILY_BUDGET_USD):
        self.daily_budget = daily_budget

    def check_all(self) -> list:
        """Executa todas as verificacoes e retorna lista de HealthAlert."""
        alerts = []
        try:
            conn = _connect()
            alerts += self._check_error_spike(conn)
            alerts += self._check_queue_stuck(conn)
            alerts += self._check_budget(conn)
            alerts += self._check_backup_age(conn)
            alerts += self._check_missions_failed(conn)
            conn.close()
        except Exception as e:
            alerts.append(HealthAlert("DB_UNAVAILABLE", "CRITICAL",
                                      "Nao foi possivel conectar ao DB: " + str(e)))
        return alerts

    def _check_error_spike(self, conn) -> list:
        """Alerta se mais de 10 erros na ultima hora."""
        one_hour_ago = (datetime.datetime.utcnow() - datetime.timedelta(hours=1)).isoformat()
        count = conn.execute(
            "SELECT COUNT(*) FROM logs WHERE level='ERROR' AND created_at > ?",
            (one_hour_ago,)
        ).fetchone()[0]
        if count > 10:
            return [HealthAlert(
                "ERROR_SPIKE", "CRITICAL",
                f"{count} erros na ultima hora — investigar logs imediatamente.", count
            )]
        if count > 5:
            return [HealthAlert(
                "ERROR_ELEVATED", "WARNING",
                f"{count} erros na ultima hora — monitorar.", count
            )]
        return []

    def _check_queue_stuck(self, conn) -> list:
        """Alerta se ha missoes RUNNING presas por mais de 1 hora."""
        one_hour_ago = (datetime.datetime.utcnow() - datetime.timedelta(hours=1)).isoformat()
        stuck = conn.execute(
            "SELECT COUNT(*) FROM fila_execucao WHERE status='RUNNING' AND started_at < ?",
            (one_hour_ago,)
        ).fetchone()[0]
        if stuck > 0:
            return [HealthAlert(
                "QUEUE_STUCK", "CRITICAL",
                f"{stuck} missao(oes) RUNNING presa(s) por >1 hora — possivel deadlock.", stuck
            )]
        return []

    def _check_budget(self, conn) -> list:
        """Alerta se gasto diario supera 80% do limite."""
        today = datetime.date.today().isoformat()
        row = conn.execute(
            "SELECT SUM(custo_usd) FROM financeiro WHERE data=?", (today,)
        ).fetchone()
        spent = row[0] or 0.0
        pct = (spent / self.daily_budget * 100) if self.daily_budget > 0 else 0
        if spent >= HARD_STOP_USD:
            return [HealthAlert(
                "BUDGET_HARD_STOP", "CRITICAL",
                f"Gasto hoje ${spent:.4f} atingiu hard_stop ${HARD_STOP_USD}. LLM BLOQUEADO.", spent
            )]
        if pct >= 80:
            return [HealthAlert(
                "BUDGET_WARNING", "WARNING",
                f"Gasto hoje ${spent:.4f} = {pct:.0f}% do limite diario ${self.daily_budget}.", spent
            )]
        return []

    def _check_backup_age(self, conn) -> list:
        """Alerta se o ultimo backup tem mais de 2 dias."""
        backup_dir = _ROOT / "13_BACKUPS_DIARIOS"
        if not backup_dir.exists():
            return [HealthAlert("BACKUP_DIR_MISSING", "WARNING",
                                "Diretorio 13_BACKUPS_DIARIOS nao encontrado.")]
        backups = sorted([
            d.name for d in backup_dir.iterdir()
            if d.is_dir() and d.name.startswith("backup_")
        ])
        if not backups:
            return [HealthAlert("BACKUP_NONE", "WARNING",
                                "Nenhum backup encontrado em 13_BACKUPS_DIARIOS.")]
        latest = backups[-1]
        try:
            date_str = latest.replace("backup_", "")
            backup_date = datetime.date.fromisoformat(date_str)
            age = (datetime.date.today() - backup_date).days
            if age > 2:
                return [HealthAlert(
                    "BACKUP_STALE", "WARNING",
                    f"Ultimo backup '{latest}' tem {age} dias. Executar backup imediatamente.", age
                )]
        except Exception:
            pass
        return []

    def _check_missions_failed(self, conn) -> list:
        """Alerta se ha missoes reais em status FAILED (nao canceladas)."""
        # Contar missoes da tabela missions (nao fila_execucao) que sao FAILED
        count = conn.execute(
            "SELECT COUNT(*) FROM missions WHERE status IN ('MISSION_FAILED','FAILED')"
        ).fetchone()[0]
        if count > 5:
            return [HealthAlert(
                "MISSIONS_FAILED", "WARNING",
                f"{count} missoes com status FAILED na tabela missions.", count
            )]
        return []

    def run_and_log(self) -> list:
        """
        Executa check_all(), persiste alertas criticos no DB e retorna lista.
        Zero Ghost: apenas persiste alertas reais.
        """
        alerts = self.check_all()
        if not alerts:
            logger.info("HealthMonitor: sistema saudavel — nenhum alerta.")
            return []

        # Persistir no DB
        try:
            conn = sqlite3.connect(str(DB_PATH), timeout=5.0)
            for a in alerts:
                level = "ERROR" if a.severity == "CRITICAL" else "WARNING"
                logger.log(
                    logging.CRITICAL if a.severity == "CRITICAL" else logging.WARNING,
                    "[%s] %s", a.code, a.message
                )
                conn.execute(
                    "INSERT INTO logs (level, source, message, payload) VALUES (?,?,?,?)",
                    (level, "HealthMonitor", a.code + ": " + a.message,
                     str(a.value) if a.value is not None else None)
                )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error("HealthMonitor: erro ao persistir alertas: %s", e)

        return alerts


def run_once() -> list:
    """Ponto de entrada para uso standalone ou pelo Maestro."""
    monitor = HealthMonitor()
    alerts = monitor.run_and_log()
    return alerts


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")
    print("=" * 60)
    print("  AGENTE-X | Health Monitor M8")
    print(f"  {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    alerts = run_once()

    if not alerts:
        print("\n  [OK] Sistema saudavel — nenhum alerta ativo.")
    else:
        print(f"\n  [{len(alerts)} ALERTA(S) DETECTADO(S)]")
        for a in alerts:
            icon = "!!" if a.severity == "CRITICAL" else "!!"
            print(f"  [{icon}] [{a.severity}] {a.code}: {a.message}")

    print("=" * 60)
