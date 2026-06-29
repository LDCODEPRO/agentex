"""
AGENTE-X | The Maestro — Runtime 24/7
O loop de execução contínua do agente.
Processa a fila de missões (fila_execucao), executa com ReAct Engine,
registra resultados e mantém o agente vivo 24/7.

Modos:
  --daemon    : roda em loop infinito processando a fila
  --once      : processa a fila uma vez e encerra
  --task GOAL : executa uma tarefa específica imediatamente
"""
import sys
import time
import signal
import logging
import argparse
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "01_CORE" / "orchestrator"))
sys.path.insert(0, str(_ROOT / "02_MEMORY" / "long_term"))
sys.path.insert(0, str(_ROOT / "01_CORE" / "mission_engine"))

from react_engine import ReActEngine
from memory_manager import MemoryManager
from mission_brain import MissionBrain

# --- Logging ---
LOG_DIR = _ROOT / "09_LOGS"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    filename=str(LOG_DIR / "maestro.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("Maestro")

POLL_INTERVAL = 10   # segundos entre polls da fila
HEARTBEAT_INTERVAL = 60  # segundos entre heartbeats no log

BANNER = """
╔══════════════════════════════════════════════════════╗
║           AGENTE-X | The Maestro Boot               ║
║         Runtime 24/7 — Zero Ghost Protocol          ║
╚══════════════════════════════════════════════════════╝
"""


class Maestro:
    """
    Orquestrador principal do AGENTE-X.
    Gerencia o ciclo de vida das missões e mantém o agente operacional.
    """

    def __init__(self):
        self.mm = MemoryManager()
        self._running = False
        self._last_heartbeat = 0
        self._tasks_processed = 0
        self._last_knowledge_seed = 0  # timestamp do ultimo seed de conhecimento
        self._last_auto_tuner    = 0  # timestamp do ultimo auto-tuning (M8)

        # Configurar shutdown gracioso
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

        # Recuperar itens orfaos da sessao anterior
        self._recover_stuck_running()

    def _recover_stuck_running(self, timeout_minutes: int = 60) -> int:
        """
        Detecta e recupera itens RUNNING orfaos (processo que crashou sem finalizar).
        Itens com started_at ha mais de timeout_minutes sao marcados FAILED.
        Zero Ghost: opera apenas sobre dados reais do banco.
        """
        import sqlite3
        db_path = str(_ROOT / "02_MEMORY" / "agente_x.db")
        try:
            conn = sqlite3.connect(db_path)
            result = conn.execute("""
                UPDATE fila_execucao
                SET status = 'FAILED',
                    finished_at = strftime('%Y-%m-%dT%H:%M:%S', 'now')
                WHERE status = 'RUNNING'
                AND CAST((strftime('%s','now') - strftime('%s', started_at)) AS INTEGER)
                    > ?
            """, (timeout_minutes * 60,))
            recovered = result.rowcount
            conn.commit()
            conn.close()
            if recovered > 0:
                logger.warning("Recovery: %d itens RUNNING orfaos -> FAILED", recovered)
                print(f"[Maestro] Recovery: {recovered} item(s) orfao(s) resetados para FAILED.")
            return recovered
        except Exception as e:
            logger.error("Erro no recovery de orfaos: %s", e)
            return 0

    def _handle_shutdown(self, sig, frame):
        print(f"\n[Maestro] Sinal {sig} recebido. Encerrando com segurança...")
        logger.info("Shutdown solicitado. Tasks processadas nesta sessão: %d", self._tasks_processed)
        self._running = False

    # ------------------------------------------------------------------
    # Modo Daemon: loop infinito
    # ------------------------------------------------------------------

    def run_daemon(self) -> None:
        """Loop 24/7. Processa fila, aguarda, repete."""
        print(BANNER)
        print(f"[Maestro] Iniciando em modo DAEMON às {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"[Maestro] Poll interval: {POLL_INTERVAL}s | Ctrl+C para encerrar")
        logger.info("Maestro daemon iniciado.")
        self._running = True

        while self._running:
            try:
                self._heartbeat()
                self._process_next_in_queue()
                time.sleep(POLL_INTERVAL)
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error("Erro no loop principal: %s", e)
                time.sleep(POLL_INTERVAL)

        print("\n[Maestro] Encerrado.")
        logger.info("Maestro daemon encerrado. Total processado: %d", self._tasks_processed)

    # ------------------------------------------------------------------
    # Modo Once: processa a fila e encerra
    # ------------------------------------------------------------------

    def run_once(self) -> int:
        """Processa todas as missões destravadas na fila e retorna o número processadas."""
        print(BANNER)
        print("[Maestro] Modo ONE-SHOT — processando fila completa...")
        processed = 0
        while True:
            item = self._dequeue_ready_item()
            if not item:
                break
            self._execute_item(item)
            processed += 1
        print(f"[Maestro] Concluído. {processed} item(s) processados.")
        return processed

    # ------------------------------------------------------------------
    # Modo Task: executa uma tarefa específica diretamente
    # ------------------------------------------------------------------

    def run_task(self, goal: str, verbose: bool = True) -> str:
        """Executa uma tarefa específica imediatamente, sem passar pela fila."""
        print(BANNER)
        print(f"[Maestro] Executando tarefa direta:")
        print(f"  Goal: {goal}\n")
        logger.info("Tarefa direta: %s", goal)

        engine = ReActEngine(session_id=f"direct_{int(time.time())}")
        self.mm.log("INFO", "Maestro", f"Tarefa direta iniciada: {goal[:100]}")

        try:
            result = engine.run(goal=goal, verbose=verbose)
            self.mm.log("INFO", "Maestro", f"Tarefa concluída: {result[:100]}")
            self._tasks_processed += 1
            return result
        except Exception as e:
            error = f"Erro na execução: {e}"
            logger.error(error)
            self.mm.log("ERROR", "Maestro", error)
            return error

    # ------------------------------------------------------------------
    # Processamento da fila
    # ------------------------------------------------------------------

    def _dequeue_ready_item(self) -> Optional[dict]:
        """
        Pega o próximo item da fila cujo grafo de dependências esteja satisfeito.
        Garante que missões dependentes não iniciem fora de ordem.
        """
        from dependency_graph import DependencyGraph
        graph = DependencyGraph()
        
        with self.mm._conn() as conn:
            # Buscar todos os itens queued
            rows = conn.execute(
                "SELECT * FROM fila_execucao WHERE status='QUEUED' ORDER BY priority ASC, id ASC"
            ).fetchall()
            
            for row in rows:
                item = dict(row)
                if graph.can_start(item["mission_code"]):
                    # Marcar como RUNNING no banco de dados da fila
                    conn.execute(
                        "UPDATE fila_execucao SET status='RUNNING', started_at=strftime('%Y-%m-%dT%H:%M:%S','now') WHERE id=?",
                        (item["id"],),
                    )
                    return item
            return None

    def _process_next_in_queue(self) -> bool:
        """Tenta pegar e executar o próximo item destravado da fila. Retorna True se processou algo."""
        item = self._dequeue_ready_item()
        if not item:
            return False

        print(f"\n[Maestro] {datetime.now().strftime('%H:%M:%S')} | Executando: {item['mission_code']}")
        logger.info("Dequeue: id=%d mission=%s", item["id"], item["mission_code"])

        self._execute_item(item)
        return True


    def _execute_item(self, item: dict) -> None:
        """Executa um item da fila usando o ReAct Engine."""
        import json
        from mission_state_manager import MissionStateManager
        
        state_mgr = MissionStateManager()
        payload = {}
        if item.get("payload"):
            try:
                payload = json.loads(item["payload"])
            except Exception:
                pass

        goal = payload.get("goal", f"Executar missão: {item['mission_code']}")
        engine = ReActEngine(session_id=f"queue_{item['id']}")
        
        # Transicionar missão para RUNNING no banco de dados principal
        state_mgr.transition(item["mission_code"], "MISSION_RUNNING", f"Executando via Maestro: {goal[:50]}")

        try:
            result = engine.run(goal=goal, verbose=True)
            self.mm.finish_queue_item(item["id"], status="DONE")
            
            # Se a resposta do ReAct contiver "FALHA" ou "ERRO" ou "SAFE_MODE"
            if "FALHA" in result or "ERRO" in result or "SAFE_MODE" in result:
                state_mgr.transition(item["mission_code"], "MISSION_FAILED", f"ReAct encerrou com falha: {result[:80]}")
            else:
                state_mgr.transition(item["mission_code"], "MISSION_VALIDATED", f"ReAct concluiu com sucesso: {result[:80]}")
                
            self.mm.log("INFO", "Maestro", f"Queue item {item['id']} concluído: {result[:80]}")
            self._tasks_processed += 1
        except Exception as e:
            self.mm.finish_queue_item(item["id"], status="FAILED")
            state_mgr.transition(item["mission_code"], "MISSION_FAILED", f"Erro crítico na execução: {str(e)[:80]}")
            logger.error("Queue item %d falhou: %s", item["id"], e)


    # ------------------------------------------------------------------
    # Heartbeat
    # ------------------------------------------------------------------

    def _heartbeat(self) -> None:
        now = time.time()
        if now - self._last_heartbeat >= HEARTBEAT_INTERVAL:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            status = self.mm.audit_summary()
            logger.info(
                "HEARTBEAT | %s | tasks_session=%d | queue_pending=%d | errors=%d",
                ts,
                self._tasks_processed,
                status["fila"]["queued"],
                status["logs"]["errors"],
            )
            self._last_heartbeat = now
            # Verificar e executar backup diario se necessario
            self._daily_backup_if_needed()
            # Limpeza de stats antigos do AntiLoopGuard (a cada heartbeat)
            self._cleanup_rate_stats()
            # Health check: alertas proativos de saude do sistema (M8)
            self._run_health_check()
            # Seed de conhecimento: executa uma vez a cada 6 horas
            if now - self._last_knowledge_seed >= 21600:
                self._seed_knowledge()
            # Auto-tuner: analisa e aplica ajustes de parametros a cada 6 horas (M8)
            if now - self._last_auto_tuner >= 21600:
                self._run_auto_tuner()

    def _seed_knowledge(self) -> None:
        """
        Executa o Hermes Knowledge Seeder a cada 6 horas para autodidatismo continuo.
        Zero Ghost: apenas dados reais injetados — sem fabricacao.
        """
        try:
            import importlib.util, sys as _s
            seeder_path = _ROOT / "04_SKILLS" / "hermes_knowledge_seeder.py"
            spec = importlib.util.spec_from_file_location("hermes_knowledge_seeder", seeder_path)
            mod  = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            total = mod.main()
            self._last_knowledge_seed = time.time()
            logger.info("Knowledge seed concluido: %d registros na base", total)
        except Exception as e:
            logger.warning("Erro no knowledge seed: %s", e)

    def _run_health_check(self) -> None:
        """Executa HealthMonitor M8 a cada heartbeat. Alertas criticos vao para o log."""
        try:
            import importlib.util as _ilu, sys as _s
            hm_path = _ROOT / "05_HEALTH" / "health_monitor.py"
            if hm_path.exists():
                spec = _ilu.spec_from_file_location("health_monitor", hm_path)
                mod  = _ilu.module_from_spec(spec)
                spec.loader.exec_module(mod)
                alerts = mod.run_once()
                if alerts:
                    logger.warning("HealthMonitor: %d alerta(s) — ver logs para detalhes.", len(alerts))
        except Exception as e:
            logger.debug("HealthMonitor ignorado: %s", e)

    def _run_auto_tuner(self) -> None:
        """
        Executa AutoTuner M8 a cada 6 horas — analisa historico real e aplica
        recomendacoes de parametros no knowledge base.
        Zero Ghost: nenhum ajuste baseado em estimativas.
        """
        try:
            import importlib.util as _ilu
            at_path = _ROOT / "05_HEALTH" / "auto_tuner.py"
            if at_path.exists():
                spec = _ilu.spec_from_file_location("auto_tuner", at_path)
                mod  = _ilu.module_from_spec(spec)
                spec.loader.exec_module(mod)
                recs = mod.run(apply=True)  # aplica no knowledge base
                issues = recs.get("issues_detected", [])
                persisted = recs.get("facts_persisted", 0)
                heartbeat_rec = recs.get("heartbeat_interval", HEARTBEAT_INTERVAL)
                logger.info(
                    "AutoTuner executado: %d fatos persistidos | %d issues | heartbeat_rec=%ds",
                    persisted, len(issues), heartbeat_rec,
                )
                if issues:
                    for issue in issues:
                        logger.warning("AutoTuner issue: %s", issue)
            self._last_auto_tuner = time.time()
        except Exception as e:
            logger.debug("AutoTuner ignorado: %s", e)
            self._last_auto_tuner = time.time()  # evitar retry em loop

    def _cleanup_rate_stats(self) -> None:
        """Remove entradas antigas de rate_limit_stats (>1 hora) para evitar crescimento sem limite."""
        try:
            import sys as _s
            _s.path.insert(0, str(_ROOT / "01_CORE" / "validation"))
            from anti_loop_guard import AntiLoopGuard
            guard = AntiLoopGuard()
            guard.clear_old_stats()
        except Exception as e:
            logger.debug("Cleanup rate_stats ignorado: %s", e)

    def _daily_backup_if_needed(self) -> None:
        """
        Executa o backup diario automaticamente se ainda nao foi feito hoje.
        Verifica a pasta 13_BACKUPS_DIARIOS/backup_YYYY-MM-DD.
        Zero Ghost: opera apenas se o backup nao existir fisicamente.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        backup_dir = _ROOT / "13_BACKUPS_DIARIOS" / f"backup_{today}"
        if backup_dir.exists():
            return  # Backup de hoje ja existe

        logger.info("Backup diario ausente para %s — iniciando SaveManager...", today)
        print(f"[Maestro] Backup diario de {today} ausente — executando...")
        try:
            sys.path.insert(0, str(_ROOT / "10_GITHUB"))
            from save_manager import SaveManager
            sm = SaveManager()
            results = sm.run_full_backup()
            ok_count = sum(1 for v in results.values() if v.get("ok"))
            logger.info("Backup diario concluido: %d/3 OK", ok_count)
            print(f"[Maestro] Backup diario: {ok_count}/3 OK")
        except Exception as e:
            logger.error("Erro no backup diario: %s", e)
            print(f"[Maestro] Erro no backup diario: {e}")


# ------------------------------------------------------------------
# Entry point CLI
# ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="AGENTE-X | The Maestro Boot")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--daemon", action="store_true", help="Modo 24/7: loop infinito processando a fila")
    group.add_argument("--once", action="store_true", help="Processa a fila uma vez e encerra")
    group.add_argument("--task", type=str, metavar="GOAL", help="Executa uma tarefa específica agora")
    group.add_argument("--macro", type=str, metavar="GOAL", help="Córtex: Injeta Macro Objetivo quebrando dependências via LLM")
    parser.add_argument("--quiet", action="store_true", help="Reduz output (sem verbose)")

    args = parser.parse_args()
    maestro = Maestro()

    if args.daemon:
        maestro.run_daemon()
    elif args.once:
        maestro.run_once()
    elif args.macro:
        print(BANNER)
        print(f"[Maestro] Analisando MACRO GOAL no Córtex Frontal: {args.macro}")
        brain = MissionBrain()
        plan = brain.generate_plan(args.macro)
        if plan:
            brain.ingest_plan(plan, args.macro)
            print(f"[Maestro] Plano: {len(plan)} subtarefas injetadas na fila.")
        else:
            print("[Maestro] Falha: nenhum plano gerado. Verificar providers LLM e logs.")
    elif args.task:
        result = maestro.run_task(args.task, verbose=not args.quiet)
        print(f"[Maestro] Resultado: {result}")
    else:
        print(BANNER)
        maestro.run_once()


if __name__ == "__main__":
    main()
