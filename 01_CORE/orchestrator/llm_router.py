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

# Modelo por especialidade da tarefa (task_type -> modelo real).
# Tarefas LEVES nao entram aqui de proposito: sem override, o Ollama local
# (custo zero) as atende primeiro. As demais usam o DeepSeek V4 Pro
# (lancado 2026-04-24: 1.6T params, 1M contexto, modo thinking) — o topo real.
# NOTA: deepseek-chat/reasoner sao legados e serao depreciados em 2026-07-24.
_TASK_MODEL_MAP = {
    "CODING": {
        "claude": "claude-3-5-sonnet-20241022",
        "openai": "gpt-4o",
        "openrouter": "nousresearch/hermes-3-llama-3-70b",
        "deepseek": "deepseek-v4-pro",
        "gemini": "gemini-2.0-flash",
        "ollama": "qwen3:8b",
    },
    "DEBUGGING": {
        "claude": "claude-3-5-sonnet-20241022",
        "openai": "gpt-4o",
        "openrouter": "nousresearch/hermes-3-llama-3-70b",
        "deepseek": "deepseek-v4-pro",
        "gemini": "gemini-2.0-flash",
        "ollama": "qwen3:8b",
    },
    "ARCHITECTURE": {
        "claude": "claude-3-5-sonnet-20241022",
        "openai": "gpt-4o",
        "openrouter": "nousresearch/hermes-3-llama-3-70b",
        "deepseek": "deepseek-v4-pro",
        "gemini": "gemini-2.0-flash",
        "ollama": "qwen3:8b",
    },
    "GOVERNANCE": {
        "claude": "claude-3-5-haiku-20241022",
        "openai": "gpt-4o-mini",
        "openrouter": "nousresearch/hermes-3-llama-3-8b",
        "deepseek": "deepseek-v4-pro",
        "gemini": "gemini-2.0-flash",
        "ollama": "qwen3:8b",
    },
    "FORENSIC": {
        "claude": "claude-3-5-sonnet-20241022",
        "openai": "gpt-4o",
        "openrouter": "nousresearch/hermes-3-llama-3-70b",
        "deepseek": "deepseek-v4-pro",
        "gemini": "gemini-2.0-flash",
        "ollama": "qwen3:8b",
    },
    "MISSION_EXECUTION": {
        "claude": "claude-3-5-sonnet-20241022",
        "openai": "gpt-4o",
        "openrouter": "nousresearch/hermes-3-llama-3-70b",
        "deepseek": "deepseek-v4-pro",
        "gemini": "gemini-2.0-flash",
        "ollama": "qwen3:8b",
    },
    "GENERAL_CHAT": {
        "claude": "claude-3-5-haiku-20241022",
        "openai": "gpt-4o-mini",
        "openrouter": "nousresearch/hermes-3-llama-3-8b",
        "deepseek": "deepseek-v4-pro",
        "gemini": "gemini-2.0-flash",
        "ollama": "qwen3:8b",
    },
}

_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_ROOT / ".env", override=True)

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
    Roteador de LLM otimizado para custo e focado em Claude e OpenAI primarios.
    Ordem de tentativa:
      1. Claude / Anthropic API (com Prompt Caching ativado)
      2. OpenAI API (caching automatico)
      3. DeepSeek API
      4. Gemini / Google API
      5. Ollama (local, privado, custo zero)
    Sem fallback para resposta simulada: falha com excecao real.
    """

    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")
    # Timeout proprio do Ollama (separado do self.timeout dos provedores pagos):
    # em CPU-only (sem GPU, ex: VPS), prefill do system prompt completo (SOUL+director+AGENTS.md)
    # facilmente passa de 60s. Custo zero -> pode esperar mais sem problema.
    OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "240"))

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
        # think=False desliga o "raciocinio" do qwen3 -> resposta MUITO mais rapida
        # (o thinking deixava o cerebro lento demais e estourava o timeout de 60s).
        payload = {"model": model, "messages": messages, "stream": False, "think": False}
        r = requests.post(
            f"{self.OLLAMA_HOST}/api/chat",
            json=payload,
            timeout=self.OLLAMA_TIMEOUT,
        )
        r.raise_for_status()
        return r.json()["message"]["content"]

    def _call_studio(self, url: str, prompt: str) -> str:
        """Ponte de assinatura LOCAL do Diretor (ex: Studio de Posts). Custo ZERO.
        Contrato: POST {message, history:[]} -> {reply}. O login/assinatura ficam
        inteiramente na ponte (o Diretor opera); aqui so trocamos texto via HTTP local."""
        r = requests.post(url, json={"message": prompt, "history": []}, timeout=self.timeout)
        r.raise_for_status()
        data = r.json()
        return data.get("reply") or data.get("response") or str(data)

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
        """Chamada nativa para Anthropic Claude API com suporte a Prompt Caching."""
        api_key = os.getenv("CLAUDE_API_KEY", "")
        if not _key_valid(api_key):
            raise ValueError("CLAUDE_API_KEY nao configurada")

        # Separar system message das mensagens (formato Anthropic)
        anthropic_messages = [m for m in messages if m["role"] != "system"]
        if not anthropic_messages:
            anthropic_messages = [{"role": "user", "content": "Ola"}]

        # Ativar cache_control no system prompt (reduz custos em ate 90% para prompts longos)
        system_blocks = [
            {
                "type": "text",
                "text": system,
                "cache_control": {"type": "ephemeral"}
            }
        ]

        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "anthropic-beta": "prompt-caching-2024-07-31",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "max_tokens": 4096,
            "system": system_blocks,
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

    def _call_openrouter(self, messages: list, model: str) -> str:
        """Chamada nativa para OpenRouter API (compativel com OpenAI)."""
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        if not _key_valid(api_key):
            raise ValueError("OPENROUTER_API_KEY nao configurada")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://github.com/LDCODEPRO/agentex",
            "X-Title": "Agente X",
            "Content-Type": "application/json",
        }
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json={"model": model, "messages": messages},
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

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
        interactive: bool = False,
    ) -> dict:
        """
        Roteia o prompt para o melhor provider disponivel (Claude -> OpenAI -> DeepSeek -> Gemini -> Ollama).
        Retorna dict com: provider, model, response, latency_ms, timestamp.
        Lanca RuntimeError se todos os providers falharem.

        interactive=True marca chat em tempo real (humano esperando resposta):
        sai da regra de custo zero do daemon e usa provedores pagos baratos pra
        responder em segundos em vez de minutos no Ollama CPU-only. Continua sob
        o teto AGENTE_X_DAILY_LIMIT_USD/HARD_STOP_USD (FinanceEngine.finance_preflight).
        """
        purpose = "CHAT_INTERACTIVE" if interactive else "GENERAL"
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

        # Classificar tipo de tarefa
        task_type = None
        if _CLASSIFIER and prompt:
            classification = _CLASSIFIER.classify(prompt)
            task_type = classification.get("task_type", "GENERAL_CHAT")
            logger.info("Task classificada: %s", task_type)

        def get_model_for(provider: str, default_model: str) -> str:
            if model:
                return model
            if task_type:
                suggested_map = _TASK_MODEL_MAP.get(task_type)
                if suggested_map and provider in suggested_map:
                    return suggested_map[provider]
            return default_model

        # 0. STUDIO BRIDGE — assinatura via ponte local do Diretor. Prioridade MAXIMA, custo ZERO.
        # So ativa se STUDIO_BRIDGE_URL estiver no .env E a ponte estiver no ar; senao cai pro fallback.
        studio_url = os.getenv("STUDIO_BRIDGE_URL", "")
        if studio_url:
            try:
                t0 = time.time()
                resp = self._call_studio(studio_url, prompt or "Continue.")
                if resp and resp.strip():
                    return self._build_result("studio", "assinatura", resp, t0)
            except Exception as e:
                errors.append(f"studio: {e}")
                logger.warning("Studio bridge indisponivel (caindo pro fallback): %s", e)

        # 1. Claude (Anthropic) - Prioridade Máxima de Assinatura Direta + Caching
        claude_key = os.getenv("CLAUDE_API_KEY", "")
        if _key_valid(claude_key):
            try:
                m = get_model_for("claude", "claude-3-5-haiku-20241022")
                if _FINANCE:
                    ok, reason = _FINANCE.finance_preflight(
                        provider="claude", model=m,
                        est_input=len(prompt or "") // 4,
                        est_output=500,
                        purpose=purpose,
                    )
                    if not ok:
                        raise RuntimeError(f"[FinanceEngine] Bloqueado: {reason}")

                t0 = time.time()
                resp = self._call_anthropic(messages, m, system)
                result = self._build_result("claude", m, resp, t0)
                if _FINANCE:
                    tokens_in = len(prompt or "") // 4
                    tokens_out = len(resp) // 4
                    _FINANCE.record_usage("claude", m, tokens_in, tokens_out)
                return result
            except Exception as e:
                errors.append(f"claude: {e}")
                logger.warning("Claude falhou: %s", e)

        # 2. OpenAI - Segunda Prioridade de Assinatura Direta
        openai_key = os.getenv("OPENAI_API_KEY", "")
        if _key_valid(openai_key):
            try:
                m = get_model_for("openai", "gpt-4o-mini")
                if _FINANCE:
                    ok, reason = _FINANCE.finance_preflight(
                        provider="openai", model=m,
                        est_input=len(prompt or "") // 4,
                        est_output=500,
                        purpose=purpose,
                    )
                    if not ok:
                        raise RuntimeError(f"[FinanceEngine] Bloqueado: {reason}")

                t0 = time.time()
                resp = self._call_openai_compatible(
                    "https://api.openai.com/v1/chat/completions",
                    openai_key, messages, m
                )
                result = self._build_result("openai", m, resp, t0)
                if _FINANCE:
                    tokens_in = len(prompt or "") // 4
                    tokens_out = len(resp) // 4
                    _FINANCE.record_usage("openai", m, tokens_in, tokens_out)
                return result
            except Exception as e:
                errors.append(f"openai: {e}")
                logger.warning("OpenAI falhou: %s", e)

        # 3. OpenRouter (Opcional)
        openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
        if _key_valid(openrouter_key):
            try:
                m = get_model_for("openrouter", "nousresearch/hermes-3-llama-3-8b")
                if _FINANCE:
                    ok, reason = _FINANCE.finance_preflight(
                        provider="openrouter", model=m,
                        est_input=len(prompt or "") // 4,
                        est_output=500,
                        purpose=purpose,
                    )
                    if not ok:
                        raise RuntimeError(f"[FinanceEngine] Bloqueado: {reason}")

                t0 = time.time()
                resp = self._call_openrouter(messages, m)
                result = self._build_result("openrouter", m, resp, t0)
                if _FINANCE:
                    tokens_in = len(prompt or "") // 4
                    tokens_out = len(resp) // 4
                    _FINANCE.record_usage("openrouter", m, tokens_in, tokens_out)
                return result
            except Exception as e:
                errors.append(f"openrouter: {e}")
                logger.warning("OpenRouter falhou: %s", e)

        # 3. DeepSeek (Terceira Prioridade)
        deepseek_key = os.getenv("DEEPSEEK_API_KEY", "")
        if _key_valid(deepseek_key):
            try:
                m = get_model_for("deepseek", "deepseek-v4-pro")
                if _FINANCE:
                    ok, reason = _FINANCE.finance_preflight(
                        provider="deepseek", model=m,
                        est_input=len(prompt or "") // 4,
                        est_output=500,
                        purpose=purpose,
                    )
                    if not ok:
                        raise RuntimeError(f"[FinanceEngine] Bloqueado: {reason}")

                t0 = time.time()
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

        # 4. Gemini (Quarta Prioridade)
        gemini_key = os.getenv("GEMINI_API_KEY", "")
        if _key_valid(gemini_key):
            try:
                m = get_model_for("gemini", "gemini-2.0-flash")
                if _FINANCE:
                    ok, reason = _FINANCE.finance_preflight(
                        provider="gemini", model=m,
                        est_input=len(prompt or "") // 4,
                        est_output=500,
                        purpose=purpose,
                    )
                    if not ok:
                        raise RuntimeError(f"[FinanceEngine] Bloqueado: {reason}")

                t0 = time.time()
                resp = self._call_gemini(messages, m)
                result = self._build_result("gemini", m, resp, t0)
                if _FINANCE:
                    tokens_in = len(prompt or "") // 4
                    tokens_out = len(resp) // 4
                    _FINANCE.record_usage("gemini", m, tokens_in, tokens_out)
                return result
            except Exception as e:
                errors.append(f"gemini: {e}")
                logger.warning("Gemini falhou: %s", e)

        # 5. Ollama local (Fallback de Custo Zero)
        if self._is_ollama_alive():
            try:
                t0 = time.time()
                m = get_model_for("ollama", self.OLLAMA_MODEL)
                resp = self._call_ollama(messages, m)
                return self._build_result("ollama", m, resp, t0)
            except Exception as e:
                errors.append(f"ollama: {e}")
                logger.warning("Ollama falhou: %s", e)

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
            "openrouter_configured": _key_valid(os.getenv("OPENROUTER_API_KEY", "")),
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
