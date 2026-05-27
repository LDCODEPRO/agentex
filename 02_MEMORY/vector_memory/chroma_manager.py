"""
AGENTE-X | Chroma Manager — Memória Vetorial
Interface real para ChromaDB persistido em disco local.
Princípio Zero Ghost: sem embeddings hardcoded ou retornos simulados.
"""

import logging
from pathlib import Path
from typing import Optional

_ROOT = Path(__file__).resolve().parent.parent.parent
CHROMA_PATH = _ROOT / "02_MEMORY" / "vector"

logger = logging.getLogger("ChromaManager")


class ChromaManager:
    """
    Gerenciador de memória vetorial com ChromaDB persistido em disco.
    Usa embeddings padrão do ChromaDB (all-MiniLM-L6-v2 via sentence-transformers).
    """

    def __init__(self, persist_dir: Path = CHROMA_PATH, collection_name: str = "agente_x_memory"):
        try:
            import chromadb
            from chromadb.config import Settings

            persist_dir.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(path=str(persist_dir))
            self._collection = self._client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            self._available = True
            logger.info("ChromaDB inicializado: %s | Coleção: %s", persist_dir, collection_name)

        except ImportError:
            self._available = False
            logger.error("chromadb não instalado. Execute: pip install chromadb")
        except Exception as e:
            self._available = False
            logger.error("Falha ao inicializar ChromaDB: %s", e)

    def _require_available(self):
        if not self._available:
            raise RuntimeError("ChromaDB não está disponível. Verifique instalação e logs.")

    # ------------------------------------------------------------------
    # Operações principais
    # ------------------------------------------------------------------

    def add_memory(
        self,
        doc_id: str,
        text: str,
        metadata: Optional[dict] = None,
    ) -> None:
        """
        Adiciona ou atualiza um documento na memória vetorial.
        doc_id deve ser único (ex: 'mission:M3', 'fact:zero_ghost_policy').
        """
        self._require_available()
        self._collection.upsert(
            ids=[doc_id],
            documents=[text],
            metadatas=[metadata or {}],
        )
        logger.info("Memória vetorial: upsert doc_id=%s", doc_id)

    def search_memory(
        self,
        query: str,
        n_results: int = 5,
        where: Optional[dict] = None,
    ) -> list[dict]:
        """
        Busca semântica na memória vetorial.
        Retorna lista de dicts com: id, document, metadata, distance.
        """
        self._require_available()
        kwargs = {"query_texts": [query], "n_results": n_results}
        if where:
            kwargs["where"] = where

        results = self._collection.query(**kwargs)

        output = []
        ids = results.get("ids", [[]])[0]
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for i, doc_id in enumerate(ids):
            output.append({
                "id": doc_id,
                "document": docs[i],
                "metadata": metas[i],
                "distance": distances[i],
            })
        return output

    def delete_memory(self, doc_id: str) -> None:
        """Remove um documento da coleção vetorial."""
        self._require_available()
        self._collection.delete(ids=[doc_id])
        logger.info("Memória vetorial: deletado doc_id=%s", doc_id)

    def count(self) -> int:
        """Retorna o total de documentos na coleção."""
        self._require_available()
        return self._collection.count()

    def status(self) -> dict:
        return {
            "available": self._available,
            "persist_dir": str(CHROMA_PATH),
            "collection_count": self.count() if self._available else -1,
        }


if __name__ == "__main__":
    cm = ChromaManager()
    print("Status ChromaDB:", cm.status())

    # Teste real de escrita e leitura
    cm.add_memory(
        doc_id="rule:zero_ghost",
        text="Zero Ghost Policy: nenhum código, dado ou resposta pode ser simulado ou mockado no AGENTE-X.",
        metadata={"category": "RULE", "source": "REGRA_INTEGRIDADE_ABSOLUTA"},
    )
    results = cm.search_memory("simulação proibida mock")
    print(f"Busca retornou {len(results)} resultado(s):")
    for r in results:
        print(f"  [{r['id']}] dist={r['distance']:.4f} — {r['document'][:80]}")
