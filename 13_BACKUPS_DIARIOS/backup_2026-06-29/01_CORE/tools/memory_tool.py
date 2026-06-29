"""
AGENTE-X | Memory Tool
Interface SQLite + ChromaDB (opcional). Degrada graciosamente sem ChromaDB.
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT / "02_MEMORY" / "long_term"))
sys.path.insert(0, str(_ROOT / "02_MEMORY" / "vector_memory"))
sys.path.insert(0, str(_ROOT / "01_CORE" / "tools"))

from base_tool import BaseTool


class MemoryTool(BaseTool):
    name = "memory_tool"
    description = (
        "Acessa a memoria persistente do agente. "
        "Operacoes: save, recall, search, log."
    )
    parameters = {
        "operation": "save | recall | search | log",
        "category": "(save/recall) categoria: RULE, FACT, DECISION, CONTEXT, SKILL",
        "key": "(save) chave unica",
        "value": "(save/log) conteudo",
        "query": "(search) texto para busca semantica",
        "limit": "(recall/search) maximo de resultados, padrao 5",
    }

    def __init__(self):
        self._mm = None
        self._cm = None

    def _get_mm(self):
        if self._mm is None:
            from memory_manager import MemoryManager
            self._mm = MemoryManager()
        return self._mm

    def _get_cm(self):
        if self._cm is None:
            try:
                from chroma_manager import ChromaManager
                cm = ChromaManager()
                if not getattr(cm, "_available", False):
                    return None
                self._cm = cm
            except Exception:
                return None
        return self._cm

    def execute(self, operation: str, category: str = "CONTEXT",
                key: str = "", value: str = "", query: str = "", limit: int = 5) -> str:
        try:
            if operation == "save":
                if not key or not value:
                    return "[MemoryTool] 'key' e 'value' sao obrigatorios para save."
                self._get_mm().upsert_knowledge(
                    category=category.upper(), key=key, value=value, source="agent_runtime"
                )
                cm = self._get_cm()
                if cm is not None:
                    try:
                        cm.add_memory(
                            doc_id=category.lower() + ":" + key,
                            text=key + ": " + value,
                            metadata={"category": category.upper(), "key": key},
                        )
                    except Exception:
                        pass
                return "[MemoryTool] Salvo: [" + category + "] " + key

            elif operation == "recall":
                items = self._get_mm().search_knowledge(category=category.upper())[:int(limit)]
                if not items:
                    return "[MemoryTool] Nenhum item em categoria '" + category + "'."
                lines = []
                for i in items:
                    lines.append("[" + i["category"] + "] " + i["key"] + ": " + i["value"][:120])
                return "\n".join(lines)

            elif operation == "search":
                if not query:
                    return "[MemoryTool] 'query' e obrigatorio para search."
                cm = self._get_cm()
                if cm is None:
                    return "[MemoryTool] ChromaDB nao disponivel. Use 'recall' para busca por categoria."
                results = cm.search_memory(query=query, n_results=int(limit))
                if not results:
                    return "[MemoryTool] Nenhum resultado semantico encontrado."
                lines = []
                for r in results:
                    lines.append("[dist=" + str(round(r["distance"],3)) + "] " + r["document"][:150])
                return "\n".join(lines)

            elif operation == "log":
                if not value:
                    return "[MemoryTool] 'value' e obrigatorio para log."
                self._get_mm().log(level="INFO", source="agent_tool", message=value)
                return "[MemoryTool] Evento registrado."

            else:
                return "[MemoryTool] Operacao desconhecida: " + operation + ". Use: save | recall | search | log"

        except Exception as e:
            return "[MemoryTool] Erro: " + str(e)

    def schema(self) -> str:
        return (
            "### memory_tool\n"
            "Acessa memoria SQLite persistente.\n"
            "Parametros: operation (save|recall|search|log), category, key, value, query, limit\n"
            "Exemplos:\n"
            "  save: operation=save category=FACT key=minha_chave value=meu_valor\n"
            "  recall: operation=recall category=RULE limit=5"
        )
