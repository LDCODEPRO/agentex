"""
AGENTE-X | Web Tool
Busca na web e fetch de URLs. Real, sem mocks.
"""
import sys
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT / "01_CORE" / "tools"))

try:
    import requests
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

from base_tool import BaseTool

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; AgentX/1.0; research bot)"}
_TIMEOUT = 15


class WebTool(BaseTool):
    name = "web_tool"
    description = "Busca na web. Operacoes: fetch (baixa pagina), search (busca DuckDuckGo)."
    parameters = {
        "operation": "fetch | search",
        "url": "(fetch) URL completa com https://",
        "query": "(search) termos de busca",
        "limit": "(search) maximo de resultados, padrao 5",
    }

    def execute(self, operation: str, url: str = "", query: str = "", limit: int = 5) -> str:
        if not _HAS_REQUESTS:
            return "[WebTool] requests nao instalado. Execute: pip install requests"
        if operation == "fetch":
            return self._fetch(url)
        elif operation == "search":
            return self._search(query, int(limit))
        else:
            return "[WebTool] Operacao desconhecida: " + operation + ". Use: fetch | search"

    def _fetch(self, url: str) -> str:
        if not url.startswith("http"):
            return "[WebTool] URL deve comecar com http:// ou https://"
        try:
            r = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
            r.raise_for_status()
            text = r.text
            text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL)
            text = re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=re.DOTALL)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()
            if len(text) > 6000:
                text = text[:6000] + "\n... [TRUNCADO]"
            return text or "[pagina sem conteudo]"
        except Exception as e:
            return "[WebTool] Erro ao fazer fetch: " + str(e)

    def _search(self, query: str, limit: int = 5) -> str:
        if not query:
            return "[WebTool] query nao pode ser vazio."
        try:
            params = {"q": query, "format": "json", "no_redirect": "1", "no_html": "1"}
            r = requests.get("https://api.duckduckgo.com/", params=params,
                             headers=_HEADERS, timeout=_TIMEOUT)
            r.raise_for_status()
            data = r.json()
            results = []
            abstract = data.get("AbstractText", "")
            if abstract:
                results.append("[RESUMO] " + abstract[:300])
                src = data.get("AbstractURL", "")
                if src:
                    results.append("   Fonte: " + src)
            for t in data.get("RelatedTopics", [])[:limit]:
                if isinstance(t, dict) and t.get("Text"):
                    results.append("- " + t["Text"][:200])
            if not results:
                return "[WebTool] Nenhum resultado para: " + query
            return "\n".join(results)
        except Exception as e:
            return "[WebTool] Erro na busca: " + str(e)

    def schema(self) -> str:
        lines = [
            "### web_tool",
            "Busca na web ou faz fetch de URL.",
            "Parametros: operation (fetch|search), url, query, limit",
            'Exemplo: {"tool": "web_tool", "tool_input": {"operation": "search", "query": "python"}}',
        ]
        return "\n".join(lines)
