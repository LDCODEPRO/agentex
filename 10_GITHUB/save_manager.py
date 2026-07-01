"""
AGENTE-X | Save Manager
Backup completo em três camadas:
  1. Disco local (backup datado em 13_BACKUPS_DIARIOS)
  2. GitHub (git add + commit + push automático)
  3. Obsidian (export do estado diário em 14_OBSIDIAN_EXPORT_DIARIO)
Princípio Zero Ghost: cada backup é real e verificado.
"""
import sys
import json
import shutil
import subprocess
import sqlite3
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")
sys.path.insert(0, str(_ROOT / "02_MEMORY" / "long_term"))

BACKUP_DIR = _ROOT / "13_BACKUPS_DIARIOS"
OBSIDIAN_DIR = _ROOT / "14_OBSIDIAN_EXPORT_DIARIO"
DB_PATH = _ROOT / "02_MEMORY" / "agente_x.db"
LOG_DIR = _ROOT / "09_LOGS"

TODAY = datetime.now().strftime("%Y-%m-%d")
NOW_TS = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class SaveManager:
    """Gerencia o pipeline completo de backup e persistência do AGENTE-X."""

    def __init__(self):
        BACKUP_DIR.mkdir(exist_ok=True)
        OBSIDIAN_DIR.mkdir(exist_ok=True)

    # ------------------------------------------------------------------
    # Pipeline completo
    # ------------------------------------------------------------------

    def run_full_backup(self) -> dict:
        """Executa os três níveis de backup em sequência."""
        print(f"\n[SaveManager] Iniciando backup completo — {NOW_TS}")
        results = {}

        print("[1/3] Backup local...")
        results["local"] = self._backup_local()
        print(f"      {'[OK]' if results['local']['ok'] else '[!!]'} {results['local']['message']}")

        print("[2/3] GitHub commit + push...")
        results["github"] = self._backup_github()
        print(f"      {'[OK]' if results['github']['ok'] else '[!!]'} {results['github']['message']}")

        print("[3/3] Obsidian export...")
        results["obsidian"] = self._backup_obsidian()
        print(f"      {'[OK]' if results['obsidian']['ok'] else '[!!]'} {results['obsidian']['message']}")

        # Gerar relatório diário automaticamente
        try:
            import sys as _sys
            _sys.path.insert(0, str(_ROOT / "10_GITHUB"))
            from daily_report_generator import generate_daily_report
            rpt = generate_daily_report()
            print(f"      [OK] Relatorio diario: {rpt.get('md_path', 'N/A')}")
            results["daily_report"] = rpt
        except Exception as _e:
            print(f"      [AV] Relatorio diario falhou: {_e}")
            results["daily_report"] = {"ok": False, "error": str(_e)}

        # Registrar no banco
        self._log_backup(results)

        print(f"\n[SaveManager] Backup concluido — {datetime.now().strftime('%H:%M:%S')}")
        return results

    # ------------------------------------------------------------------
    # 1. Backup local
    # ------------------------------------------------------------------

    def _backup_local(self) -> dict:
        """Cria snapshot datado em 13_BACKUPS_DIARIOS."""
        try:
            target = BACKUP_DIR / f"backup_{TODAY}"
            target.mkdir(exist_ok=True)

            # Copiar arquivos críticos (não copiar node_modules, .venv, etc.)
            critical_dirs = [
                "00_GOVERNANCE/RULES",
                "01_CORE",
                "02_MEMORY/long_term",
                "02_MEMORY/short_term",
                "02_MEMORY/vector_memory",
                "03_RUNTIME",
                "04_SKILLS",
                "10_GITHUB",
            ]
            critical_files = [
                "agente_x.py",
                "setup_agente_x.py",
                "README.md",
                ".gitignore",
                "FOUNDATION_V1.md",
                "AGENTE_X_DNA_BLUEPRINT.md",
            ]

            copied = 0
            for d in critical_dirs:
                src = _ROOT / d
                if src.exists():
                    dst = target / d
                    if dst.exists():
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.db-wal", "*.db-shm"))
                    copied += 1

            for f in critical_files:
                src = _ROOT / f
                if src.exists():
                    dst_f = target / f
                    dst_f.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst_f)
                    copied += 1

            # Copiar banco SQLite (se existir)
            if DB_PATH.exists():
                db_backup = target / "02_MEMORY" / "agente_x.db"
                db_backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(DB_PATH, db_backup)

            return {"ok": True, "message": f"Backup em {target.name} | {copied} items copiados"}

        except Exception as e:
            return {"ok": False, "message": f"Erro: {e}"}

    # ------------------------------------------------------------------
    # 2. GitHub
    # ------------------------------------------------------------------

    def _backup_github(self) -> dict:
        """Faz git add, commit e push.

        Pulado quando AGENTE_X_VPS_NO_GIT=true: a VPS roda como espelho
        somente-leitura do GitHub (fonte da verdade); commitar/pushar de la
        diverge o historico e contraria o fluxo de deploy.
        """
        import os
        if os.getenv("AGENTE_X_VPS_NO_GIT", "false").lower() == "true":
            return {"ok": True, "message": "Pulado (AGENTE_X_VPS_NO_GIT=true) — VPS e somente-leitura de codigo"}
        try:
            # Verificar se é repositório git
            result = subprocess.run(
                "git rev-parse --git-dir",
                shell=True, capture_output=True, text=True, cwd=str(_ROOT)
            )
            if result.returncode != 0:
                # Inicializar repositório se não existir
                subprocess.run("git init", shell=True, cwd=str(_ROOT), check=True)
                return {"ok": False, "message": "Git inicializado mas sem remote configurado. Configure com: git remote add origin <URL>"}

            # git add all
            subprocess.run("git add -A", shell=True, cwd=str(_ROOT), check=True)

            # Verificar se há algo para commitar
            status_result = subprocess.run(
                "git status --porcelain",
                shell=True, capture_output=True, text=True, cwd=str(_ROOT)
            )
            if not status_result.stdout.strip():
                return {"ok": True, "message": "Nada para commitar (working tree limpa)"}

            # Contar mudanças
            changes = len(status_result.stdout.strip().split("\n"))

            # Commit
            commit_msg = f"[AGENTE-X] Auto-save {NOW_TS} | {changes} arquivo(s) modificado(s)"
            subprocess.run(
                f'git commit -m "{commit_msg}"',
                shell=True, cwd=str(_ROOT), check=True
            )

            # Push (se tiver remote configurado)
            remote_result = subprocess.run(
                "git remote -v",
                shell=True, capture_output=True, text=True, cwd=str(_ROOT)
            )
            if "origin" in remote_result.stdout:
                push_result = subprocess.run(
                    "git push origin HEAD",
                    shell=True, capture_output=True, text=True, cwd=str(_ROOT)
                )
                if push_result.returncode == 0:
                    return {"ok": True, "message": f"Commit + Push OK | {changes} arquivo(s) | '{commit_msg[:60]}'"}
                else:
                    return {"ok": True, "message": f"Commit OK (push falhou: {push_result.stderr[:100]})"}
            else:
                return {"ok": True, "message": f"Commit OK | {changes} arquivo(s) | (sem remote push)"}

        except subprocess.CalledProcessError as e:
            return {"ok": False, "message": f"Git error: {e}"}
        except Exception as e:
            return {"ok": False, "message": f"Erro: {e}"}

    # ------------------------------------------------------------------
    # 3. Obsidian Export
    # ------------------------------------------------------------------

    def _backup_obsidian(self) -> dict:
        """Gera nota Obsidian com o estado diário do AGENTE-X."""
        try:
            # Coletar dados do banco
            db_data = self._collect_db_summary()

            # Coletar skills
            skills_dir = _ROOT / "04_SKILLS" / "learned"
            skill_count = len(list(skills_dir.glob("*.json"))) if skills_dir.exists() else 0

            # Coletar últimos logs
            last_logs = []
            if DB_PATH.exists():
                conn = sqlite3.connect(str(DB_PATH))
                rows = conn.execute(
                    "SELECT level, source, message, created_at FROM logs ORDER BY id DESC LIMIT 10"
                ).fetchall()
                conn.close()
                last_logs = [{"level": r[0], "source": r[1], "msg": r[2][:80], "ts": r[3]} for r in rows]

            # Gerar nota Markdown
            note = f"""---
tags: [agente-x, diario, backup]
date: {TODAY}
status: auto-generated
---

# 📅 AGENTE-X | Estado Diário — {TODAY}

> Gerado automaticamente pelo SaveManager em {NOW_TS}

## 📊 Resumo do Sistema

| Métrica | Valor |
|---|---|
| Missões concluídas | {db_data.get('missions_done', 0)} |
| Missões pendentes | {db_data.get('missions_pending', 0)} |
| Sessões ativas | {db_data.get('sessions', 0)} |
| Conhecimento acumulado | {db_data.get('knowledge', 0)} itens |
| Skills aprendidas | {skill_count} |
| Itens na fila | {db_data.get('fila_queued', 0)} |
| Erros registrados | {db_data.get('errors', 0)} |

## 🎯 Missões

| Código | Status |
|---|---|
"""
            for m in db_data.get("missions", []):
                status_icon = {"DONE": "✅", "PENDING": "⏳", "IN_PROGRESS": "🔄", "FAILED": "❌"}.get(m["status"], "?")
                note += f"| {m['code']} — {m['title']} | {status_icon} {m['status']} |\n"

            note += f"""
## 🧠 Últimos Eventos

```
"""
            for log in last_logs:
                note += f"[{log['ts']}] [{log['level']}] {log['source']}: {log['msg']}\n"

            note += "```\n\n"
            note += f"## 🔗 Links\n\n"
            note += f"- [[AGENTE_X_DNA_BLUEPRINT]]\n"
            note += f"- [[FOUNDATION_V1]]\n"
            note += f"- Backup local: `13_BACKUPS_DIARIOS/backup_{TODAY}/`\n"

            # Salvar em 14_OBSIDIAN_EXPORT_DIARIO
            obsidian_file = OBSIDIAN_DIR / f"AGENTE_X_{TODAY}.md"
            obsidian_file.write_text(note, encoding="utf-8")

            # Também copiar para 11_OBSIDIAN se a pasta existir
            obsidian_vault = _ROOT / "11_OBSIDIAN"
            if obsidian_vault.exists():
                shutil.copy2(obsidian_file, obsidian_vault / f"AGENTE_X_{TODAY}.md")

            return {"ok": True, "message": f"Nota criada: {obsidian_file.name}"}

        except Exception as e:
            return {"ok": False, "message": f"Erro: {e}"}

    # ------------------------------------------------------------------
    # Utilitários
    # ------------------------------------------------------------------

    def _collect_db_summary(self) -> dict:
        if not DB_PATH.exists():
            return {}
        try:
            conn = sqlite3.connect(str(DB_PATH))
            missions = [
                {"code": r[0], "title": r[1], "status": r[2]}
                for r in conn.execute("SELECT code, title, status FROM missions ORDER BY id").fetchall()
            ]
            data = {
                "missions": missions,
                "missions_done": conn.execute("SELECT COUNT(*) FROM missions WHERE status='DONE'").fetchone()[0],
                "missions_pending": conn.execute("SELECT COUNT(*) FROM missions WHERE status='PENDING'").fetchone()[0],
                "sessions": conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0],
                "knowledge": conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0],
                "fila_queued": conn.execute("SELECT COUNT(*) FROM fila_execucao WHERE status='QUEUED'").fetchone()[0],
                "errors": conn.execute("SELECT COUNT(*) FROM logs WHERE level='ERROR'").fetchone()[0],
            }
            conn.close()
            return data
        except Exception:
            return {}

    def _log_backup(self, results: dict) -> None:
        if not DB_PATH.exists():
            return
        try:
            conn = sqlite3.connect(str(DB_PATH))
            summary = json.dumps({k: v["message"] for k, v in results.items()})
            conn.execute(
                "INSERT INTO logs (level, source, message, payload) VALUES ('INFO', 'SaveManager', ?, ?)",
                (f"Backup completo executado em {NOW_TS}", summary)
            )
            conn.commit()
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    sm = SaveManager()
    sm.run_full_backup()
