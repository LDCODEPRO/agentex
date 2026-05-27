"""
AGENTE-X | Web Tool
Busca na web e fetch de URLs. Real, sem mocks.
"""
import sys
import json
import re
from pathlib import Path
from typing import Optional

_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT / "00_GOVERNANCE" / "RULES"))

try:
    import requests
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

from base_tool import BaseTool

# User-agent neutro para evitar bloqueios
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AgentX/1.0; research bot)"
}
_TIMEOUT = 15


class WebTool(BaseTool):
    name = "web_tool"
    description = (
        "Busca informações na web. "
        "Operações: fetch (baixa página), search (busca via DuckDuckGo)."
    )
    parameters = {
        "operation": "fetch | search",
        "url": "(fetch) URL completa com https://",
        "query": "(search) termos de busca",
        "limit": "(search) número máximo de resultados, padrão 5",
    }

    def execute(
        self,
        operation: str,
        url: str = "",
        query: str = "",
        limit: int = 5,
    ) -> str:
        if not _HAS_REQUESTS:
            return "[WebTool] requests não instalado. Execute: pip install requests"

        if operation == "fetch":
            return self._fetch(url)
        elif operation == "search":
            return self._search(query, int(limit))
        else:
            return f"[WebTool] Operação desconhecida: {operation}. Use: fetch | search"

    def _fetch(self, url: str) -> str:
        if not url.startswith("http"):
            return "[WebTool] URL deve começar com http:// ou https://"
        try:
            r = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
            r.raise_for_status()
            text = r.text

            # Remover tags HTML para texto limpo
            text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL)
            text = re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=re.DOTALL)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()

            # Limitar tamanho
            if len(text) > 6000:
                text = text[:6000] + "\n... [TRUNCADO]"
            return text or "[página sem conteúdo]"
        except requests.exceptions.Timeout:
            return f"[WebTool] Timeout ao acessar: {url}"
        except requests.exceptions.HTTPError as e:
            return f"[WebTool] HTTP {e.response.status_code}: {url}"
        except Exception as e:
            return f"[WebTool] Erro ao fazer fetch: {e}"

    def _search(self, query: str, limit: int = 5) -> str:
        """Busca via DuckDuckGo Instant Answer API (sem chave de API necessária)."""
        if not query:
            return "[WebTool] 'query' não pode ser vazio."
        try:
            params = {
                "q": query,
                "format": "json",
                "no_redirect": "1",
                "no_html": "1",
                "skip_disambig": "1",
            }
            r = requests.get(
                "https://api.duckduckgo.com/",
                params=params,
                headers=_HEADERS,
                timeout=_TIMEOUT,
            )
            r.raise_for_status()
            data = r.json()

            results = []

            # Abstract (resposta direta)
            if data.get("AbstractText"):
                results.append(f"📌 {data['AbstractText'][:300]}")
                if data.get("AbstractURL"):
                    results.append(f"   Fonte: {data['AbstractURL']}")

            # RelatedTopics
            topics = data.get("RelatedTopics", [])[:limit]
            for t in topics:
                if isinstance(t, dict) and t.get("Text"):
                    results.append(f"• {t['Text'][:200]}")
                    if t.get("FirstURL"):
                        results.append(f"  → {t['FirstURL']}")

            if not results:
                # Fallback: busca HTML da página de resultados
                r2 = requests.get(
                    f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}",
                    headers=_HEADERS,
                    timeout=_TIMEOUT,
                )
                snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', r2.text)
                urls = re.findall(r'class="result__url"[^>]*>(.*?)</span>', r2.text)
                for i, (s, u) in enumerate(zip(snippets[:limit], urls[:limit])):
                    clean = re.sub(r"<[^>]+>", "", s).strip()
                    results.append(f"• {clean}\n  → {u.strip()}")
                if not results:
                    return f"[WebTool] Nenhum resultado para: {query}"

            return "\n".join(results)
        except Exception as e:
            return f"[WebTool] Erro na busca: {e}"
