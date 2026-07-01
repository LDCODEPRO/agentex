"""
AGENTE-X | File Tool
Leitura, escrita e listagem de arquivos -- integrado ao safe_gate.
"""
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


def _log_blocked(op: str, target: str, msg: str) -> None:
    """Registra bloqueio do safe_gate para a tela de Seguranca do cockpit."""
    try:
        _mm.log("WARNING", "safe_gate", f"{op} bloqueado: {target} | {msg}")
    except Exception:
        pass


class FileTool(BaseTool):
    name = "file_tool"
    description = "Le, escreve ou lista arquivos no projeto. Operacoes validadas pelo safe_gate."
    parameters = {
        "operation": "read | write | list | exists",
        "path": "caminho relativo a raiz do projeto",
        "content": "(apenas para write) conteudo a escrever",
    }

    def execute(self, operation: str, path: str, content: str = "") -> str:
        target = _ROOT / path

        if operation == "read":
            ok, msg = validate_action("READ", str(target))
            if not ok:
                return f"[FileTool] BLOQUEADO: {msg}"
            if not target.exists():
                return f"[FileTool] Arquivo nao encontrado: {path}"
            try:
                text = target.read_text(encoding="utf-8", errors="replace")
                if len(text) > 8000:
                    text = text[:8000] + f"\n... [TRUNCADO -- {len(text)} chars total]"
                return text
            except Exception as e:
                return f"[FileTool] Erro ao ler: {e}"

        elif operation == "write":
            ok, msg = validate_action("WRITE", str(target))
            if not ok:
                _log_blocked("WRITE", str(path), msg)
                return f"[FileTool] BLOQUEADO: {msg}"
            
            # Syntax Guard para scripts Python
            if target.suffix == ".py":
                import ast
                try:
                    ast.parse(content)
                except SyntaxError as se:
                    return (
                        f"[FileTool] ESCRITA BLOQUEADA: Erro de sintaxe Python detectado!\n"
                        f"  Arquivo: {path}\n"
                        f"  Linha: {se.lineno}\n"
                        f"  Coluna: {se.offset}\n"
                        f"  Erro: {se.msg}\n"
                        f"  Código problemático: '{se.text.strip() if se.text else ''}'\n"
                        f"Por favor, corrija a sintaxe antes de salvar."
                    )
            
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                return f"[FileTool] Escrito: {path} ({len(content)} chars)"
            except Exception as e:
                return f"[FileTool] Erro ao escrever: {e}"


        elif operation == "list":
            ok, msg = validate_action("READ", str(target))
            if not ok:
                return f"[FileTool] BLOQUEADO: {msg}"
            if not target.exists():
                return f"[FileTool] Diretorio nao encontrado: {path}"
            try:
                entries = sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name))
                lines = []
                for e in entries[:100]:
                    tag = "[DIR]" if e.is_dir() else "[ARQ]"
                    lines.append(f"{tag} {e.name}")
                return "\n".join(lines) or "[vazio]"
            except Exception as e:
                return f"[FileTool] Erro ao listar: {e}"

        elif operation == "exists":
            return str(target.exists())

        else:
            return f"[FileTool] Operacao desconhecida: {operation}. Use: read | write | list | exists"

    def schema(self) -> str:
        return (
            "### file_tool\n"
            "Le, escreve ou lista arquivos no projeto.\n"
            "Parametros: operation (read|write|list|exists), path (relativo), content (so para write)\n"
            'Exemplo: {"tool": "file_tool", "tool_input": {"operation": "list", "path": "04_SKILLS"}}'
        )
