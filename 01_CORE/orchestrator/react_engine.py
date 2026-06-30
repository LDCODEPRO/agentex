"""
AGENTE-X | ReAct Engine
O coração cognitivo do agente.
Implementa o ciclo: Thought → Action → Action Input → Observation → (repete)
Até atingir: Final Answer

Inspirado em:
- ReAct (Yao et al., 2022): Synergizing Reasoning and Acting in LLMs
- Hermes Agent: self-improving loop com skill extraction
- Replit Agent 4: plan-while-build, self-testing
"""
import re
import sys
import json
import time
import logging
from pathlib import Path
from typing import Optional

_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT / "02_MEMORY" / "short_term"))
sys.path.insert(0, str(_ROOT / "04_SKILLS"))

from llm_router import LLMRouter
from tool_registry import ToolRegistry
from context_manager import ContextManager
from skill_manager import SkillManager

# Hallucination Guard — valida respostas LLM contra contexto real (portado do PHANDORA)
try:
    import sys as _sys
    _sys.path.insert(0, str(_ROOT / "01_CORE" / "validation"))
    from hallucination_guard import HallucinationGuard as _HallucinationGuard
    _HGUARD = _HallucinationGuard()
except Exception as e:
    raise RuntimeError(f"FALHA CRÍTICA: Não foi possível carregar Hallucination Guard. (FAIL CLOSED) - {e}")

# Carregar perfil do Diretor (few-shot + estilo de comunicacao)
try:
    sys.path.insert(0, str(_ROOT / "12_CONFIG"))
    from director_profile import get_director_context
    _DIRECTOR_CONTEXT = get_director_context()

except Exception:
    _DIRECTOR_CONTEXT = ""

# ------------------------------------------------------------------
# Carregar SOUL.md e AGENTS.md (padrao Hermes)
# ------------------------------------------------------------------

def _load_soul_md() -> str:
    """Carrega identidade do agente de 12_CONFIG/SOUL.md."""
    soul_path = _ROOT / "12_CONFIG" / "SOUL.md"
    if soul_path.exists():
        content = soul_path.read_text(encoding="utf-8").strip()
        return content[:20000]  # cap Hermes-style
    return ""

def _load_agents_md() -> str:
    """Carrega regras do projeto de AGENTS.md na raiz."""
    for name in ("AGENTS.md", ".hermes.md", "HERMES.md"):
        p = _ROOT / name
        if p.exists():
            content = p.read_text(encoding="utf-8").strip()
            return f"## Regras do Projeto ({name})\n\n{content[:20000]}"
    return ""

_SOUL = _load_soul_md()
_AGENTS_CONTEXT = _load_agents_md()

logging.basicConfig(
    filename=str(_ROOT / "09_LOGS" / "react_engine.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("ReActEngine")

MAX_STEPS = 20       # Limite de segurança para evitar loops infinitos
MAX_RETRIES = 2      # Retentativas se LLM não seguir o formato


# ------------------------------------------------------------------
# Prompt do sistema
# ------------------------------------------------------------------

SYSTEM_PROMPT_TEMPLATE = """{soul}

{agents_context}

{director_context}

{context_snapshot}

{tools_description}

{skills_hint}

## Formato OBRIGATORIO de resposta:

Para usar uma ferramenta:
Thought: [raciocinio sobre o que fazer agora]
Action: [nome_da_ferramenta]
Action Input: {{"param1": "valor1", "param2": "valor2"}}

Para finalizar:
Thought: [raciocinio final]
Final Answer: [resposta completa e objetiva — use [OK], numeros, indicadores visuais]

IMPORTANTE: Action Input deve ser JSON valido com aspas duplas.
NUNCA invente observacoes. NUNCA pule etapas.
"""


class ReActEngine:
    """
    Motor de raciocínio e ação do AGENTE-X.
    Combina LLM + ferramentas em um loop cognitivo real.
    """

    def __init__(self, session_id: str = None):
        self.session_id = session_id or f"session_{int(time.time())}"
        self.router = LLMRouter()
        self.registry = ToolRegistry()
        self.context = ContextManager(session_id=self.session_id)
        self.skills = SkillManager()
        self._step_log: list[str] = []
        self._tools_used: list[str] = []

    # ------------------------------------------------------------------
    # Execução principal
    # ------------------------------------------------------------------

    def run(self, goal: str, verbose: bool = True, interactive: bool = False) -> str:
        """
        Executa o loop ReAct para atingir o objetivo.
        Retorna a resposta final ou mensagem de erro.

        interactive=True: chat em tempo real com o Diretor esperando resposta.
        Sai do Ollama custo-zero (lento, CPU-only) pra provedor pago barato.
        """
        logger.info("=== NOVA EXECUÇÃO === Goal: %s", goal)
        self.context.set_goal(goal)
        self._step_log = []
        self._tools_used = []

        # Histórico da conversa (multi-turno para o LLM)
        history = []
        final_answer = None

        for step in range(1, MAX_STEPS + 1):
            if verbose:
                print(f"\n{'-'*50}")
                print(f"🔄 Passo {step}/{MAX_STEPS}")

            # Construir prompt do sistema com contexto atual
            system = SYSTEM_PROMPT_TEMPLATE.format(
                soul=_SOUL or "Voce e o AGENTE-X, agente autonomo criado para Luiz Cipolari.",
                agents_context=_AGENTS_CONTEXT,
                director_context=_DIRECTOR_CONTEXT,
                context_snapshot=self.context.get_context_snapshot(),
                tools_description=self.registry.get_tools_description(),
                skills_hint=self.skills.format_skills_for_prompt(goal),
            )

            # Construir mensagens: histórico + goal atual
            if not history:
                user_msg = f"Objetivo: {goal}"
            else:
                user_msg = "Continue. Use ferramentas se necessário. Responda no formato correto."

            # Chamada ao LLM
            try:
                result = self.router.route(
                    prompt=user_msg if not history else None,
                    system=system,
                    interactive=interactive,
                )
                # Para multi-turno, passar histórico completo
                if history:
                    # Reformatar com histórico
                    full_prompt = self._format_history(goal, history)
                    result = self.router.route(prompt=full_prompt, system=system, interactive=interactive)

                llm_response = result["response"].strip()
                provider = result["provider"]

                # Hallucination Guard: valida resposta contra contexto acumulado
                if _HGUARD and history:
                    ctx_text = " ".join(
                        str(h.get("observation", "")) for h in history[-3:]
                    )
                    hg_result = _HGUARD.guard(llm_response, ctx_text)
                    if hg_result["status"] == "SAFE_MODE_ACTIVATED":
                        alert_msg = f"HALLUCINATION_GUARD_FAILURE\nSTATUS: SAFE_MODE_ACTIVATED\nMISSION: BLOCKED\nACTION REQUIRED: HUMAN REVIEW\nRisk Score: {hg_result['risk_score']}"
                        logger.critical(alert_msg)
                        if verbose:
                            print(f"\n[CRITICAL] {alert_msg}\n")
                        return f"[SAFE_MODE] Missão bloqueada por Hallucination Guard. Requer liberação humana."
                    elif hg_result["status"] == "RESTRICTED_MODE":
                        logger.warning("HallucinationGuard RESTRICTED_MODE: risk=%.2f", hg_result["risk_score"])
                        if verbose:
                            print(f"[WARNING] RESTRICTED_MODE: Missão interrompida. Risco médio ({hg_result['risk_score']:.2f})")
                        return f"[RESTRICTED] Requer revisão de evidência para continuar."
                    elif hg_result["status"] == "WARNING":
                        logger.warning("HallucinationGuard WARNING: risk=%.2f", hg_result["risk_score"])

                if verbose:
                    print(f"[{provider}] {llm_response[:300]}{'...' if len(llm_response) > 300 else ''}")

                logger.info("Step %d | Provider: %s | Response: %s", step, provider, llm_response[:200])

            except RuntimeError as e:
                error_msg = f"Sem LLM disponível: {e}"
                logger.error(error_msg)
                return f"[ReAct] FALHA CRÍTICA: {error_msg}"

            # Parse da resposta do LLM
            parsed = self._parse_response(llm_response)

            if parsed["type"] == "final_answer":
                final_answer = parsed["content"]
                self._step_log.append(f"FINAL: {final_answer[:100]}")
                if verbose:
                    print(f"\n✅ RESPOSTA FINAL:\n{final_answer}")
                break

            elif parsed["type"] == "action":
                tool_name = parsed["tool"]
                tool_input = parsed["input"]
                thought = parsed.get("thought", "")

                if thought:
                    self.context.add_thought(thought)
                    self._step_log.append(f"THOUGHT: {thought[:80]}")

                # Executar ferramenta
                if verbose:
                    print(f"🔧 Executando: {tool_name}({json.dumps(tool_input)[:100]})")

                observation = self.registry.execute(tool_name, **tool_input)
                self._tools_used.append(tool_name)
                self.context.add_observation(tool_name, observation)
                self._step_log.append(f"ACTION: {tool_name} → {observation[:80]}")

                if verbose:
                    print(f"👁️  Observação: {observation[:200]}{'...' if len(observation) > 200 else ''}")

                logger.info("Step %d | Action: %s | Observation: %s", step, tool_name, observation[:150])

                # Adicionar ao histórico multi-turno
                history.append({
                    "thought": thought,
                    "action": tool_name,
                    "input": tool_input,
                    "observation": observation,
                })

            else:
                # LLM não seguiu o formato — tentar reformatar
                if verbose:
                    print(f"⚠️  Formato inválido. Tentando guiar...")
                history.append({
                    "thought": "formato inválido",
                    "action": "_none",
                    "input": {},
                    "observation": f"[Sistema] Resposta anterior não seguiu o formato. Responda com Thought/Action/Action Input ou Final Answer.",
                })

        else:
            # Atingiu MAX_STEPS sem resposta final
            final_answer = f"[ReAct] Limite de {MAX_STEPS} passos atingido. Último estado: {self._step_log[-1] if self._step_log else 'sem passos'}"
            logger.warning("MAX_STEPS atingido para goal: %s", goal)

        # Auto-aprendizado: salvar skill se tarefa foi complexa
        if final_answer:
            skill_id = self.skills.save_skill(
                goal=goal,
                steps=self._step_log,
                tools_used=self._tools_used,
                final_answer=final_answer,
                success="FALHA" not in final_answer and "ERRO" not in final_answer,
            )
            if skill_id:
                logger.info("Skill salva: %s", skill_id)

        return final_answer or "[ReAct] Sem resposta final."

    # ------------------------------------------------------------------
    # Parsing da resposta do LLM
    # ------------------------------------------------------------------

    def _parse_response(self, text: str) -> dict:
        """
        Parseia a resposta do LLM.
        Retorna dict com 'type': 'action' | 'final_answer' | 'invalid'
        """
        # Procurar Final Answer
        fa_match = re.search(r"Final Answer:\s*(.+)", text, re.DOTALL | re.IGNORECASE)
        if fa_match:
            return {"type": "final_answer", "content": fa_match.group(1).strip()}

        # Procurar Action + Action Input
        thought_match = re.search(r"Thought:\s*(.+?)(?=Action:|Final Answer:|$)", text, re.DOTALL | re.IGNORECASE)
        action_match = re.search(r"Action:\s*(\w+)", text, re.IGNORECASE)
        input_match = re.search(r"Action Input:\s*(\{.*?\})", text, re.DOTALL | re.IGNORECASE)

        if action_match:
            tool_name = action_match.group(1).strip().lower()
            tool_input = {}

            if input_match:
                try:
                    tool_input = json.loads(input_match.group(1))
                except json.JSONDecodeError:
                    # Tentar extrair pares chave:valor de texto livre
                    raw = input_match.group(1)
                    # Limpar aspas simples e tentar novamente
                    raw = raw.replace("'", '"')
                    try:
                        tool_input = json.loads(raw)
                    except Exception:
                        tool_input = {"raw_input": raw}

            thought = thought_match.group(1).strip() if thought_match else ""

            return {
                "type": "action",
                "thought": thought,
                "tool": tool_name,
                "input": tool_input,
            }

        return {"type": "invalid", "raw": text[:200]}

    # ------------------------------------------------------------------
    # Formatação do histórico para prompt multi-turno
    # ------------------------------------------------------------------

    def _format_history(self, goal: str, history: list[dict]) -> str:
        lines = [f"Objetivo: {goal}\n"]
        for h in history:
            if h.get("thought"):
                lines.append(f"Thought: {h['thought']}")
            if h["action"] != "_none":
                lines.append(f"Action: {h['action']}")
                lines.append(f"Action Input: {json.dumps(h['input'])}")
                lines.append(f"Observation: {h['observation'][:400]}")
            else:
                lines.append(f"Observation: {h['observation']}")
            lines.append("")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Status do sistema (usado por agente_x.py --status e CLI)
    # ------------------------------------------------------------------

    def status(self) -> dict:
        """
        Retorna status completo do runtime do agente.
        Usado por agente_x.py --status e cmd_status().
        Zero Ghost: todos os dados sao lidos de fontes reais.
        """
        router_status = self.router.status()
        tools_available = list(self.registry._tools.keys()) if hasattr(self.registry, "_tools") else []
        skills_loaded = len(self.skills._skills) if hasattr(self.skills, "_skills") else 0

        # Financeiro — se disponivel
        finance_summary = {}
        try:
            import sys as _s
            _s.path.insert(0, str(_ROOT / "01_CORE" / "finance"))
            from finance_engine import FinanceEngine
            fe = FinanceEngine()
            finance_summary = fe.summary()
        except Exception:
            pass

        return {
            "session_id":      self.session_id,
            "router_status":   router_status,
            "tools_available": tools_available,
            "skills_loaded":   skills_loaded,
            "finance":         finance_summary,
            "soul_loaded":     bool(_SOUL),
            "agents_loaded":   bool(_AGENTS_CONTEXT),
        }
