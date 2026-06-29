"""
AGENTE-X | Tool Registry
Registro central de todas as ferramentas disponíveis ao agente.
Responsável por despachar chamadas de ferramentas pelo nome.
"""
import sys
from pathlib import Path

_TOOLS_DIR = Path(__file__).resolve().parent.parent / "tools"
sys.path.insert(0, str(_TOOLS_DIR))

from file_tool import FileTool
from shell_tool import ShellTool
from memory_tool import MemoryTool
from web_tool import WebTool


class ToolRegistry:
    """
    Registro de ferramentas. Inicializa uma vez, despacha por nome.
    """

    def __init__(self):
        _tools_list = [FileTool(), ShellTool(), MemoryTool(), WebTool()]
        self._tools = {t.name: t for t in _tools_list}

    def execute(self, tool_name: str, **kwargs) -> str:
        """Executa uma ferramenta pelo nome. Retorna resultado como string."""
        tool = self._tools.get(tool_name)
        if not tool:
            available = ", ".join(self._tools.keys())
            return f"[Registry] Ferramenta '{tool_name}' não encontrada. Disponíveis: {available}"
        try:
            return tool.execute(**kwargs)
        except TypeError as e:
            return f"[Registry] Parâmetros inválidos para '{tool_name}': {e}"
        except Exception as e:
            return f"[Registry] Erro ao executar '{tool_name}': {e}"

    def get_tools_description(self) -> str:
        """Retorna a descrição de todas as ferramentas para injeção no prompt."""
        lines = ["## Ferramentas disponíveis:"]
        for tool in self._tools.values():
            lines.append(tool.schema())
        return "\n".join(lines)

    def list_names(self) -> list[str]:
        return list(self._tools.keys())
