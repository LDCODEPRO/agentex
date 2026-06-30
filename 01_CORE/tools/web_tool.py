"""
AGENTE-X | Web Tool
Busca real na web (DuckDuckGo HTML) e fetch de URLs. Real, sem mocks.
Inclui protecao SSRF: nao acessa IPs internos/loopback/metadados de nuvem.
"""
import sys
import re
import socket
import ipaddress
from pathlib import Path
from urllib.parse import urlparse, unquote

_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT / "01_CORE" / "tools"))

try:
    import requests
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

from base_tool import BaseTool

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
_HEADERS = {"User-Agent": _UA}
_TIMEOUT = 15


def _strip_html(t: str) -> str:
    t = re.sub(r"<style[^>]*>.*?</style>", " ", t, flags=re.DOTALL)
    t = re.sub(r"<script[^>]*>.*?</script>", " ", t, flags=re.DOTALL)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t).strip()


class WebTool(BaseTool):
    name = "web_tool"
    description = "Busca real na web. Operacoes: search (resultados com links), fetch (le uma pagina)."
    parameters = {
        "operation": "search | fetch",
        "query": "(search) termos de busca",
        "url": "(fetch) URL completa com https://",
        "limit": "(search) maximo de resultados, padrao 5",
    }

    def execute(self, operation: str, url: str = "", query: str = "", limit: int = 5) -> str:
        if not _HAS_REQUESTS:
            return "[WebTool] requests nao instalado. Execute: pip install requests"
        if operation == "search":
            return self._search(query, int(limit))
        elif operation == "fetch":
            return self._fetch(url)
        else:
            return "[WebTool] Operacao desconhecida: " + operation + ". Use: search | fetch"

    def _is_internal(self, url: str):
        """Retorna o motivo do bloqueio se a URL aponta p/ rede interna; None se for segura."""
        try:
            host = urlparse(url).hostname
            if not host:
                return "host vazio"
            ip = ipaddress.ip_address(socket.gethostbyname(host))
            if (ip.is_private or ip.is_loopback or ip.is_link_local
                    or ip.is_reserved or ip.is_multicast):
                return f"{host} -> {ip}"
            return None
        except Exception:
            return None  # nao resolveu: deixa o requests tratar o erro real

    def _search(self, query: str, limit: int = 5) -> str:
        if not query:
            return "[WebTool] query nao pode ser vazio."
        try:
            from ddgs import DDGS
            results = DDGS().text(query, max_results=int(limit))
            out = []
            for i, r in enumerate(results, 1):
                title = _strip_html(r.get("title", "") or "")
                href = r.get("href", "") or ""
                body = _strip_html(r.get("body", "") or "")
                line = f"{i}. {title}"
                if href:
                    line += f"\n   {href}"
                if body:
                    line += f"\n   {body[:220]}"
                out.append(line)
            if not out:
                return "[WebTool] Nenhum resultado para: " + query
            return "\n".join(out)
        except ImportError:
            return "[WebTool] lib 'ddgs' nao instalada. Execute: pip install ddgs"
        except Exception as e:
            return "[WebTool] Erro na busca: " + str(e)

    def _fetch(self, url: str) -> str:
        if not url.startswith("http"):
            return "[WebTool] URL deve comecar com http:// ou https://"
        blocked = self._is_internal(url)
        if blocked:
            return "[WebTool] BLOQUEADO (SSRF): destino interno proibido: " + blocked
        try:
            r = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT, allow_redirects=True)
            # Revalida o destino final apos redirects (defesa contra redirect -> interno)
            final_blocked = self._is_internal(r.url)
            if final_blocked:
                return "[WebTool] BLOQUEADO (SSRF apos redirect): " + final_blocked
            r.raise_for_status()
            text = _strip_html(r.text)
            if len(text) > 6000:
                text = text[:6000] + "\n... [TRUNCADO]"
            return text or "[pagina sem conteudo]"
        except Exception as e:
            return "[WebTool] Erro ao fazer fetch: " + str(e)

    def schema(self) -> str:
        lines = [
            "### web_tool",
            "Busca real na web ou le uma pagina.",
            "Parametros: operation (search|fetch), query, url, limit",
            'Exemplo busca: {"tool": "web_tool", "tool_input": {"operation": "search", "query": "cortes virais youtube 2026"}}',
            'Exemplo ler pagina: {"tool": "web_tool", "tool_input": {"operation": "fetch", "url": "https://..."}}',
        ]
        return "\n".join(lines)
