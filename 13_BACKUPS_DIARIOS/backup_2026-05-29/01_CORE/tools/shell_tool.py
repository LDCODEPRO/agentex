"""
AGENTE-X | Shell Tool
Executa comandos no terminal local — integrado ao safe_gate.
Timeout configurável. Captura stdout + stderr.
"""
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT / "00_GOVERNANCE" / "RULES"))

from base_tool import BaseTool
from safe_gate import validate_action

DEFAULT_TIMEOUT = 30  # segundos


class ShellTool(BaseTool):
    name = "shell_tool"
    description = "Executa comandos no terminal Windows/Linux. Bloqueado por safe_gate contra comandos destrutivos."
    parameters = {
        "command": "comando a executar (string)",
        "timeout": f"(opcional) timeout em segundos, padrão {DEFAULT_TIMEOUT}",
        "cwd": "(opcional) diretório de trabalho, padrão raiz do projeto",
    }

    def execute(self, command: str, timeout: int = DEFAULT_TIMEOUT, cwd: str = None) -> str:
        # Validar via safe_gate
        ok, msg = validate_action("SHELL", command)
        if not ok:
            return f"[ShellTool] BLOQUEADO: {msg}"

        work_dir = str(_ROOT / cwd) if cwd else str(_ROOT)

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=int(timeout),
                cwd=work_dir,
            )
            output = ""
            if result.stdout.strip():
                output += result.stdout.strip()
            if result.stderr.strip():
                output += f"\n[STDERR] {result.stderr.strip()}"
            if result.returncode != 0:
                output += f"\n[EXIT CODE] {result.returncode}"

            # Limitar saída
            if len(output) > 4000:
                output = output[:4000] + "\n... [TRUNCADO]"

            return output.strip() or "[sem saída]"

        except subprocess.TimeoutExpired:
            return f"[ShellTool] TIMEOUT após {timeout}s"
        except Exception as e:
            return f"[ShellTool] Erro: {e}"
