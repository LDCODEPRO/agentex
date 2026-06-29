"""
AGENTE-X | Entry Point Principal
O ponto de entrada unificado para o AGENTE-X.

Uso:
  python agente_x.py                     # modo interativo
  python agente_x.py --daemon            # 24/7 loop
  python agente_x.py --task "seu goal"   # tarefa direta
  python agente_x.py --status            # status do sistema
  python agente_x.py --enqueue "goal"    # adiciona à fila (prioridade opcional: --priority 1-10)
  python agente_x.py --save              # backup → GitHub + Obsidian
"""
import sys
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "01_CORE" / "orchestrator"))
sys.path.insert(0, str(ROOT / "02_MEMORY" / "long_term"))
sys.path.insert(0, str(ROOT / "03_RUNTIME"))

BANNER = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     █████╗  ██████╗ ███████╗███╗   ██╗████████╗███████╗     ║
║    ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝██╔════╝     ║
║    ███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║   █████╗       ║
║    ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   ██╔══╝       ║
║    ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║   ███████╗     ║
║    ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚══════╝    ║
║                          — X —                               ║
║         Agente Soberano | Zero Ghost | 24/7 Ready            ║
╚══════════════════════════════════════════════════════════════╝
"""


def cmd_status():
    """Exibe o status completo do sistema."""
    from react_engine import ReActEngine
    from memory_manager import MemoryManager

    print(BANNER)
    engine = ReActEngine()
    mm = MemoryManager()

    status = engine.status()
    summary = mm.audit_summary()

    print("═══════════════════ STATUS DO AGENTE-X ═══════════════════")
    print(f"\n🔌 LLM Router:")
    rs = status["router_status"]
    print(f"   Ollama: {'🟢 ONLINE' if rs['ollama_alive'] else '🔴 OFFLINE'} ({rs['ollama_host']})")
    print(f"   DeepSeek: {'✅ Configurado' if rs['deepseek_configured'] else '⚠️  Placeholder'}")
    print(f"   OpenAI: {'✅ Configurado' if rs['openai_configured'] else '⚠️  Placeholder'}")

    print(f"\n🧠 Cognição:")
    print(f"   Ferramentas ativas: {', '.join(status['tools_available'])}")
    print(f"   Skills aprendidas: {status['skills_loaded']}")

    print(f"\n💾 Memória (SQLite):")
    print(f"   Missões: {summary['missions']['total']} total | {summary['missions']['done']} concluídas | {summary['missions']['failed']} falhas")
    print(f"   Sessões: {summary['sessions']}")
    print(f"   Conhecimento: {summary['knowledge']} itens")
    print(f"   Fila: {summary['fila']['queued']} aguardando | {summary['fila']['running']} rodando")
    print(f"   Logs: {summary['logs']['total']} eventos | {summary['logs']['errors']} erros")

    print("\n══════════════════════════════════════════════════════════\n")


def cmd_enqueue(goal: str, priority: int = 5):
    """Adiciona uma tarefa à fila de execução."""
    from memory_manager import MemoryManager
    import json

    mm = MemoryManager()
    item_id = mm.enqueue_mission(
        mission_code=f"TASK_{int(__import__('time').time())}",
        priority=priority,
        payload={"goal": goal},
    )
    print(f"✅ Tarefa adicionada à fila [ID: {item_id}] | Priority: {priority}")
    print(f"   Goal: {goal}")


def cmd_save():
    """Backup completo: GitHub + Obsidian export."""
    from save_manager import SaveManager
    sm = SaveManager()
    sm.run_full_backup()


def main():
    parser = argparse.ArgumentParser(
        description="AGENTE-X — Agente Autônomo Soberano",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--daemon", action="store_true", help="Modo 24/7: loop infinito")
    parser.add_argument("--once", action="store_true", help="Processa a fila uma vez")
    parser.add_argument("--task", type=str, metavar="GOAL", help="Executa tarefa direta")
    parser.add_argument("--status", action="store_true", help="Status do sistema")
    parser.add_argument("--enqueue", type=str, metavar="GOAL", help="Adiciona à fila")
    parser.add_argument("--priority", type=int, default=5, help="Prioridade da fila (1-10)")
    parser.add_argument("--save", action="store_true", help="Backup: GitHub + Obsidian")
    parser.add_argument("--quiet", action="store_true", help="Reduz output")

    args = parser.parse_args()

    if args.status:
        cmd_status()

    elif args.enqueue:
        cmd_enqueue(args.enqueue, args.priority)

    elif args.save:
        cmd_save()

    elif args.daemon or args.once or args.task:
        from maestro import Maestro, main as maestro_main
        maestro = Maestro()
        if args.daemon:
            maestro.run_daemon()
        elif args.once:
            maestro.run_once()
        elif args.task:
            result = maestro.run_task(args.task, verbose=not args.quiet)
            print(f"\n{'='*60}")
            print(result)

    else:
        # Modo interativo
        from maestro import Maestro
        print(BANNER)
        maestro = Maestro()
        print("[AGENTE-X] Modo interativo iniciado.")
        print("[AGENTE-X] Comandos: 'status', 'salvar', 'fila: seu goal', 'sair'\n")
        while True:
            try:
                goal = input("🎯 > ").strip()
                if not goal:
                    continue
                if goal.lower() in ("sair", "exit", "quit"):
                    break
                if goal.lower() == "status":
                    cmd_status()
                    continue
                if goal.lower() == "salvar":
                    cmd_save()
                    continue
                if goal.lower().startswith("fila:"):
                    cmd_enqueue(goal[5:].strip())
                    continue
                result = maestro.run_task(goal, verbose=not args.quiet)
                print(f"\n{'═'*60}")
                print(f"✅ {result}")
                print(f"{'═'*60}\n")
            except (KeyboardInterrupt, EOFError):
                break
        print("\n[AGENTE-X] Sessão encerrada.")


if __name__ == "__main__":
    main()
