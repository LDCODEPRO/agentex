"""
AGENTE-X | File Tool
Leitura, escrita e listagem de arquivos — integrado ao safe_gate.
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT / "00_GOVERNANCE" / "RULES"))

from base_tool import BaseTool
from safe_gate import validate_action


class FileTool(BaseTool):
    name = "file_tool"
    description = "Lê, escreve ou lista arquivos no projeto. Operações validadas pelo safe_gate."
    parameters = {
        "operation": "read | write | list | exists",
        "path": "caminho do arquivo ou diretório (relativo à raiz do projeto)",
        "content": "(apenas para write) conteúdo a escrever",
    }

    def execute(self, operation: str, path: str, content: str = "") -> str:
        target = _ROOT / path

        if operation == "read":
            ok, msg = validate_action("READ", str(target))
            if not ok:
                return f"[FileTool] BLOQUEADO: {msg}"
            if not target.exists():
                return f"[FileTool] Arquivo não encontrado: {path}"
            try:
                text = target.read_text(encoding="utf-8", errors="replace")
                # Limitar saída para não explodir o contexto
                if len(text) > 8000:
                    text = text[:8000] + f"\n... [TRUNCADO — {len(text)} chars total]"
                return text
            except Exception as e:
                return f"[FileTool] Erro ao ler: {e}"

        elif operation == "write":
            ok, msg = validate_action("WRITE", str(target))
            if not ok:
                return f"[FileTool] BLOQUEADO: {msg}"
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                return f"[FileTool] Escrito com sucesso: {path} ({len(content)} chars)"
            except Exception as e:
                return f"[FileTool] Erro ao escrever: {e}"

        elif operation == "list":
            ok, msg = validate_action("READ", str(target))
            if not ok:
                return f"[FileTool] BLOQUEADO: {msg}"
            if not target.exists():
                return f"[FileTool] Diretório não encontrado: {path}"
            try:
                entries = sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name))
                lines = []
                for e in entries[:100]:
                    tag = "📁" if e.is_dir() else "📄"
                    lines.append(f"{tag} {e.name}")
                return "\n".join(lines) or "[vazio]"
            except Exception as e:
                return f"[FileTool] Erro ao listar: {e}"

        elif operation == "exists":
            return str(target.exists())

        else:
            return f"[FileTool] Operação desconhecida: {operation}. Use: read | write | list | exists"
