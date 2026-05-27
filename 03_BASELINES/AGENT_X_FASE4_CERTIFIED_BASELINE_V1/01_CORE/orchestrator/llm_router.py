"""
AGENTE-X | LLM Router
Roteador de cognicao: tenta Ollama local primeiro, fallback para APIs externas.
Principio Zero Ghost: nenhuma resposta simulada. Se falhar, falha com erro real.

Providers suportados (ordem de prioridade):
  1. Ollama (local, privado, custo zero)
  2. DeepSeek API (mais barato)
  3. Claude / Anthropic API (mais capaz)
  4. OpenAI API
"""

import os
import json
import time
import logging
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
import requests

# Finance Engine — circuit breaker financeiro
try:
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "finance"))
    from finance_engine import FinanceEngine as _FinanceEngine
    _FINANCE = _FinanceEngine()
except Exception:
    _FINANCE = None

# Task Classifier — seleciona modelo por tipo de tarefa
try:
    from task_classifier import TaskClassifier as _TaskClassifier
    _CLASSIFIER = _TaskClassifier()
except Exception:
    _CLASSIFIER = None

# Anti-Loop Guard — rate limit e profundidade de recursao
try:
    import sys as _sys2
    _sys2.path.insert(0, str(Path(__file__).resolve().parent.parent / "validation"))
    from anti_loop_guard import AntiLoopGuard as _AntiLoopGuard
    from trace_context import TraceContext as _TraceContext
    _ANTI_LOOP = _AntiLoopGuard()
except Exception:
    _ANTI_LOOP = None
    _TraceContext = None

# Modelo recomendado por tipo de task (task_type -> model_override)
_TASK_MODEL_MAP = {
    "FAST_SUMMARY":    "deepseek-v4-pro",
    "CLASSIFICATION":  "deepseek-v4-pro",
    "CODING":          "deepseek-v4-pro",
    "DEBUGGING":       "deepseek-v4-pro",
    "ARCHITECTURE":    "deepseek-v4-pro",
    "MISSION_EXECUTION": "deepseek-v4-pro",
    "GOVERNANCE":      "deepseek-v4-pro",
    "PRIVACY":         "deepseek-v4-pro",
    "FORENSIC":        "deepseek-v4-pro",
    "GENERAL_CHAT":    "deepseek-v4-pro",
}

_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_ROOT / ".env")

logging.basicConfig(
    filename=str(_ROOT / "09_LOGS" / "llm_router.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("LLMRouter")

_PLACEHOLDER = "SK-PLACEHOLDER"


def _key_valid(key: str) -> bool:
    return bool(key) and _PLACEHOLDER not in key and len(key) > 10


class LLMRouter:
    """
    Roteador de LLM com prioridade local.
    Ordem de tentativa:
      1. Ollama (local, privado, custo zero)
      2. DeepSeek API
      3. Claude / Anthropic API
      4. OpenAI API
    Sem fallback para resposta simulada: falha com excecao real.
    """

    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

    def __init__(self, timeout: int = 60):
        self.timeout = timeout

    def _is_ollama_alive(self) -> bool:
        try:
            r = requests.get(f"{self.OLLAMA_HOST}/api/tags", timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    def _call_ollama(self, messages: list, model: str = None) -> str:
        model = model or self.OLLAMA_MODEL
        payload = {"model": model, "messages": messages, "stream": False}
        r = requests.post(
            f"{self.OLLAMA_HOST}/api/chat",
            json=payload,
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()["message"]["content"]

    def _call_openai_compatible(self, url: str, api_key: str, messages: list, model: str) -> str:
        """Chamada compativel com OpenAI (DeepSeek usa o mesmo formato)."""
        if not _key_valid(api_key):
            raise ValueError("API key nao configurada ou invalida")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        r = requests.post(
            url,
            headers=headers,
            json={"model": model, "messages": messages},
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    def _call_anthropic(self, messages: list, model: str, system: str) -> str:
        """Chamada nativa para Anthropic Claude API."""
        api_key = os.getenv("CLAUDE_API_KEY", "")
        if not _key_valid(api_key):
            raise ValueError("CLAUDE_API_KEY nao configurada")

        # Separar system message das mensagens (formato Anthropic)
        anthropic_messages = [m for m in messages if m["role"] != "system"]
        if not anthropic_messages:
            anthropic_messages = [{"role": "user", "content": "Ola"}]

        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "max_tokens": 4096,
            "system": system,
            "messages": anthropic_messages,
        }
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()["content"][0]["text"]

    def _call_gemini(self, messages: list, model: str) -> str:
        """Chamada para Google Gemini API."""
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not _key_valid(api_key):
            raise ValueError("GEMINI_API_KEY nao configurada")

        # Converter mensagens para formato Gemini
        parts = []
        for m in messages:
            parts.append({"text": m["content"]})

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {"contents": [{"parts": parts}]}
        r = requests.post(url, json=payload, timeout=self.timeout)
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]

    def route(
        self,
        prompt: str,
        system: str = "Voce e o AGENTE-X, um agente soberano, preciso e sem simulacoes.",
        model: Optional[str] = None,
        agent_name: str = "AGENTE_X",
        mission_id: str = "UNKNOWN",
        depth: int = 0,
    ) -> dict:
        """
        Roteia o prompt para o melhor provider disponivel.
        Retorna dict com: provider, model, response, latency_ms, timestamp.
        Lanca RuntimeError se todos os providers falharem.
        """
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt or "Continue."},
        ]
        errors = []

        # Anti-Loop preflight — bloqueia recursao e rajadas antes de qualquer chamada
        if _ANTI_LOOP and _TraceContext:
            ctx = _TraceContext(
                mission_id=mission_id,
                current_agent=agent_name,
                depth=depth,
            )
            allowed, reason = _ANTI_LOOP.preflight(ctx)
            if not allowed:
                raise RuntimeError(f"[AntiLoopGuard] Bloqueado: {reason}")

        # Classificar tarefa e ajustar modelo se necessário
        if _CLASSIFIER and prompt:
            classification = _CLASSIFIER.classify(prompt)
            task_type = classification.get("task_type", "GENERAL_CHAT")
            confidence = classification.get("confidence", 0.0)
            if confidence >= 0.55 and model is None:
                suggested = _TASK_MODEL_MAP.get(task_type)
                if suggested:
                    model = suggested
            logger.info("Task classificada: %s (conf=%.2f)", task_type, confidence)

        # 1. Ollama local
        if self._is_ollama_alive():
            try:
                t0 = time.time()
                resp = self._call_ollama(messages, model)
                return self._build_result("ollama", model or self.OLLAMA_MODEL, resp, t0)
            except Exception as e:
                errors.append(f"ollama: {e}")
                logger.warning("Ollama falhou: %s", e)

        # 2. DeepSeek
        # Finance preflight — circuit breaker antes de qualquer chamada paga
        if _FINANCE:
            ok, reason = _FINANCE.finance_preflight(
                provider="deepseek", model=model or "deepseek-v4-pro",
                est_input=len(prompt or "") // 4,
                est_output=500,
            )
            if not ok:
                raise RuntimeError(f"[FinanceEngine] Bloqueado: {reason}")

        deepseek_key = os.getenv("DEEPSEEK_API_KEY", "")
        if _key_valid(deepseek_key):
            try:
                t0 = time.time()
                m = model or "deepseek-v4-pro"
                resp = self._call_openai_compatible(
                    "https://api.deepseek.com/v1/chat/completions",
                    deepseek_key, messages, m
                )
                result = self._build_result("deepseek", m, resp, t0)
                if _FINANCE:
                    tokens_in = len(prompt or "") // 4
                    tokens_out = len(resp) // 4
                    _FINANCE.record_usage("deepseek", m, tokens_in, tokens_out)
                return result
            except Exception as e:
                errors.append(f"deepseek: {e}")
                logger.warning("DeepSeek falhou: %s", e)

        # 3. Claude (Anthropic)
        claude_key = os.getenv("CLAUDE_API_KEY", "")
        if _key_valid(claude_key):
            try:
                t0 = time.time()
                m = model or "claude-haiku-4-5-20251001"
                resp = self._call_anthropic(messages, m, system)
                return self._build_result("claude", m, resp, t0)
            except Exception as e:
                errors.append(f"claude: {e}")
                logger.warning("Claude falhou: %s", e)

        # 4. OpenAI
        openai_key = os.getenv("OPENAI_API_KEY", "")
        if _key_valid(openai_key):
            try:
                t0 = time.time()
                m = model or "gpt-4o-mini"
                resp = self._call_openai_compatible(
                    "https://api.openai.com/v1/chat/completions",
                    openai_key, messages, m
                )
                return self._build_result("openai", m, resp, t0)
            except Exception as e:
                errors.append(f"openai: {e}")
                logger.warning("OpenAI falhou: %s", e)

        # 5. Gemini
        gemini_key = os.getenv("GEMINI_API_KEY", "")
        if _key_valid(gemini_key):
            try:
                t0 = time.time()
                m = model or "gemini-2.0-flash"
                resp = self._call_gemini(messages, m)
                return self._build_result("gemini", m, resp, t0)
            except Exception as e:
                errors.append(f"gemini: {e}")
                logger.warning("Gemini falhou: %s", e)

        # Zero Ghost: sem fallback simulado
        error_summary = " | ".join(errors) if errors else "Nenhum provider configurado"
        logger.error("Todos os providers falharam: %s", error_summary)
        raise RuntimeError(f"LLMRouter: nenhum provider disponivel. Erros: {error_summary}")

    def _build_result(self, provider: str, model: str, response: str, t0: float) -> dict:
        latency = int((time.time() - t0) * 1000)
        logger.info("Roteado via %s | modelo=%s | latencia=%dms", provider, model, latency)
        return {
            "provider": provider,
            "model": model,
            "response": response,
            "latency_ms": latency,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }

    def status(self) -> dict:
        return {
            "ollama_alive": self._is_ollama_alive(),
            "ollama_host": self.OLLAMA_HOST,
            "ollama_model": self.OLLAMA_MODEL,
            "deepseek_configured": _key_valid(os.getenv("DEEPSEEK_API_KEY", "")),
            "claude_configured": _key_valid(os.getenv("CLAUDE_API_KEY", "")),
            "openai_configured": _key_valid(os.getenv("OPENAI_API_KEY", "")),
            "gemini_configured": _key_valid(os.getenv("GEMINI_API_KEY", "")),
            "anti_loop_active": _ANTI_LOOP is not None,
            "finance_active": _FINANCE is not None,
        }

    def test_connection(self) -> dict:
        """Testa o provider disponivel com uma mensagem simples."""
        try:
            result = self.route(
                prompt="Responda apenas: AGENTE-X ONLINE",
                system="Voce e um assistente. Responda exatamente o que foi pedido.",
            )
            return {"status": "OK", **result}
        except RuntimeError as e:
            return {"status": "ERRO", "message": str(e)}


if __name__ == "__main__":
    import json
    router = LLMRouter()
    print("=== Status dos Providers ===")
    print(json.dumps(router.status(), indent=2))
