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

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "01_CORE" / "orchestrator"))
sys.path.insert(0, str(_ROOT / "02_MEMORY" / "long_term"))

from react_engine import ReActEngine
from memory_manager import MemoryManager

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

        # Configurar shutdown gracioso
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

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
        """Processa todas as missões na fila e retorna o número processadas."""
        print(BANNER)
        print("[Maestro] Modo ONE-SHOT — processando fila completa...")
        processed = 0
        while True:
            item = self.mm.dequeue_next()
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

    def _process_next_in_queue(self) -> bool:
        """Tenta pegar e executar o próximo item da fila. Retorna True se processou algo."""
        item = self.mm.dequeue_next()
        if not item:
            return False

        print(f"\n[Maestro] {datetime.now().strftime('%H:%M:%S')} | Executando: {item['mission_code']}")
        logger.info("Dequeue: id=%d mission=%s", item["id"], item["mission_code"])

        self._execute_item(item)
        return True

    def _execute_item(self, item: dict) -> None:
        """Executa um item da fila usando o ReAct Engine."""
        import json
        payload = {}
        if item.get("payload"):
            try:
                payload = json.loads(item["payload"])
            except Exception:
                pass

        goal = payload.get("goal", f"Executar missão: {item['mission_code']}")
        engine = ReActEngine(session_id=f"queue_{item['id']}")

        try:
            result = engine.run(goal=goal, verbose=True)
            self.mm.finish_queue_item(item["id"], status="DONE")
            self.mm.log("INFO", "Maestro", f"Queue item {item['id']} concluído: {result[:80]}")
            self._tasks_processed += 1
        except Exception as e:
            self.mm.finish_queue_item(item["id"], status="FAILED")
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


# ------------------------------------------------------------------
# Entry point CLI
# ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="AGENTE-X | The Maestro Boot")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--daemon", action="store_true", help="Modo 24/7: loop infinito processando a fila")
    group.add_argument("--once", action="store_true", help="Processa a fila uma vez e encerra")
    group.add_argument("--task", type=str, metavar="GOAL", help="Executa uma tarefa específica agora")
    parser.add_argument("--quiet", action="store_true", help="Reduz output (sem verbose)")

    args = parser.parse_args()
    maestro = Maestro()

    if args.daemon:
        maestro.run_daemon()
    elif args.once:
        maestro.run_once()
    elif args.task:
        result = maestro.run_task(args.task, verbose=not args.quiet)
        print(f"\n{'='*50}")
        print("RESULTADO FINAL:")
        print(result)
    else:
        # Modo interativo padrão
        print(BANNER)
        print("[Maestro] Modo interativo. Digite seu objetivo (ou 'sair' para encerrar):\n")
        while True:
            try:
                goal = input("🎯 Goal: ").strip()
                if goal.lower() in ("sair", "exit", "quit", "q"):
                    break
                if not goal:
                    continue
                result = maestro.run_task(goal, verbose=True)
                print(f"\n{'='*50}")
                print(f"✅ RESULTADO: {result}")
                print(f"{'='*50}\n")
            except (KeyboardInterrupt, EOFError):
                break
        print("\n[Maestro] Até logo.")


if __name__ == "__main__":
    main()
