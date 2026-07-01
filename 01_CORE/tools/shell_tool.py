"""
AGENTE-X | Shell Tool
Executa comandos no terminal -- integrado ao safe_gate.
"""
import shlex
import subprocess
import sys
import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent

_sg_path = _ROOT / "00_GOVERNANCE" / "safe_gate.py"
_sg_spec = importlib.util.spec_from_file_location("safe_gate_gov", str(_sg_path))
_sg_mod  = importlib.util.module_from_spec(_sg_spec)
_sg_spec.loader.exec_module(_sg_mod)
validate_action = _sg_mod.validate_action

sys.path.insert(0, str(_ROOT / "01_CORE" / "tools"))
from base_tool import BaseTool

sys.path.insert(0, str(_ROOT / "02_MEMORY" / "long_term"))
from memory_manager import MemoryManager

_mm = MemoryManager()

DEFAULT_TIMEOUT = 30


class ShellTool(BaseTool):
    name = "shell_tool"
    description = "Executa comandos no terminal. Bloqueado por safe_gate contra comandos destrutivos."
    parameters = {
        "command": "comando simples (sem &&, |, ;)",
        "timeout": f"(opcional) timeout em segundos, padrao {DEFAULT_TIMEOUT}",
        "cwd": "(opcional) diretorio de trabalho",
    }

    def execute(self, command: str, timeout: int = DEFAULT_TIMEOUT, cwd: str = None) -> str:
        ok, msg = validate_action("SHELL", command)
        if not ok:
            try:
                _mm.log("WARNING", "safe_gate", f"Comando bloqueado: {command[:200]} | {msg}")
            except Exception:
                pass
            return f"[ShellTool] BLOQUEADO: {msg}"
        work_dir = str(_ROOT / cwd) if cwd else str(_ROOT)
        try:
            # shell=False + lista de argumentos: elimina o vetor de shell injection
            # (sem shell intermediario nao ha metacaractere/expansao pra explorar).
            args = shlex.split(command, posix=(sys.platform != "win32"))
            result = subprocess.run(
                args, shell=False, capture_output=True,
                text=True, timeout=int(timeout), cwd=work_dir,
            )
            output = ""
            if result.stdout.strip():
                output += result.stdout.strip()
            if result.stderr.strip():
                output += f"\n[STDERR] {result.stderr.strip()}"
            if result.returncode != 0:
                output += f"\n[EXIT CODE] {result.returncode}"
            if len(output) > 4000:
                output = output[:4000] + "\n... [TRUNCADO]"
            return output.strip() or "[sem saida]"
        except subprocess.TimeoutExpired:
            return f"[ShellTool] TIMEOUT apos {timeout}s"
        except Exception as e:
            return f"[ShellTool] Erro: {e}"

    def schema(self) -> str:
        return (
            "### shell_tool\n"
            "Executa comando de terminal (sem &&, |, ;).\n"
            "Parametros: command (string), timeout (int), cwd (string)\n"
            'Exemplo: {"tool": "shell_tool", "tool_input": {"command": "python --version"}}'
        )
