"""
AGENTE-X | Memory Tool
Interface do agente com SQLite (long_term) e ChromaDB (vetorial).
Permite salvar, recuperar e buscar conhecimento persistido.
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT / "02_MEMORY" / "long_term"))
sys.path.insert(0, str(_ROOT / "02_MEMORY" / "vector_memory"))

from base_tool import BaseTool


class MemoryTool(BaseTool):
    name = "memory_tool"
    description = (
        "Acessa a memória persistente do agente. "
        "Operações: save (salvar fato), recall (buscar por categoria), "
        "search (busca semântica vetorial), log (registrar evento)."
    )
    parameters = {
        "operation": "save | recall | search | log",
        "category": "(save/recall) categoria do conhecimento: RULE, FACT, DECISION, CONTEXT, SKILL",
        "key": "(save) chave única do fato",
        "value": "(save/log) conteúdo a salvar",
        "query": "(search) texto para busca semântica",
        "limit": "(recall/search) máximo de resultados, padrão 5",
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
            from chroma_manager import ChromaManager
            self._cm = ChromaManager()
        return self._cm

    def execute(
        self,
        operation: str,
        category: str = "CONTEXT",
        key: str = "",
        value: str = "",
        query: str = "",
        limit: int = 5,
    ) -> str:
        try:
            if operation == "save":
                if not key or not value:
                    return "[MemoryTool] 'key' e 'value' são obrigatórios para save."
                self._get_mm().upsert_knowledge(
                    category=category.upper(),
                    key=key,
                    value=value,
                    source="agent_runtime",
                )
                # Também salvar no vetorial para buscas semânticas futuras
                self._get_cm().add_memory(
                    doc_id=f"{category.lower()}:{key}",
                    text=f"{key}: {value}",
                    metadata={"category": category.upper(), "key": key},
                )
                return f"[MemoryTool] Salvo: [{category}] {key}"

            elif operation == "recall":
                items = self._get_mm().search_knowledge(category=category.upper())[:int(limit)]
                if not items:
                    return f"[MemoryTool] Nenhum item em categoria '{category}'."
                lines = [f"[{i['category']}] {i['key']}: {i['value'][:120]}" for i in items]
                return "\n".join(lines)

            elif operation == "search":
                if not query:
                    return "[MemoryTool] 'query' é obrigatório para search."
                results = self._get_cm().search_memory(query=query, n_results=int(limit))
                if not results:
                    return "[MemoryTool] Nenhum resultado semântico encontrado."
                lines = [
                    f"[dist={r['distance']:.3f}] {r['document'][:150]}"
                    for r in results
                ]
                return "\n".join(lines)

            elif operation == "log":
                if not value:
                    return "[MemoryTool] 'value' é obrigatório para log."
                self._get_mm().log(
                    level="INFO",
                    source="agent_tool",
                    message=value,
                )
                return f"[MemoryTool] Evento registrado."

            else:
                return f"[MemoryTool] Operação desconhecida: {operation}. Use: save | recall | search | log"

        except Exception as e:
            return f"[MemoryTool] Erro: {e}"
