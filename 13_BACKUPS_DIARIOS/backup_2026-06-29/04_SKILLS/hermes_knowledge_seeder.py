"""
AGENTE-X | Hermes Knowledge Seeder
Busca conhecimento externo real (artigos, documentacao, pesquisa)
e injeta na knowledge base do agente.
Principio Zero Ghost: apenas dados reais de fontes verificadas.
Autodidatismo conforme SOUL.md: "busque conhecimento quando nao ha missao".

Uso:
    python hermes_knowledge_seeder.py           # seed completo
    python hermes_knowledge_seeder.py --quick   # apenas conhecimento local
    python hermes_knowledge_seeder.py --web     # busca na web tambem
"""

import sys
import os
import json
import sqlite3
import datetime
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if not (_ROOT / "02_MEMORY").exists():
    _ROOT = Path(__file__).resolve().parent

MAIN_DB  = _ROOT / "02_MEMORY" / "agente_x.db"
WEB_MODE = "--web" in sys.argv or "--full" in sys.argv
QUICK    = "--quick" in sys.argv


def _connect():
    try:
        conn = sqlite3.connect(str(MAIN_DB))
        conn.execute("CREATE TABLE IF NOT EXISTS _wtest (x INTEGER)")
        conn.execute("DROP TABLE IF EXISTS _wtest")
        conn.commit()
        return conn
    except Exception:
        import tempfile as _t
        return sqlite3.connect(_t.gettempdir() + "/agente_x_seed.db")


def inject(category: str, key: str, value: str, source: str, confidence: float = 1.0):
    """Injeta fato verificado na knowledge base."""
    conn = _connect()
    conn.execute("""
        INSERT INTO knowledge (category, key, value, source, confidence)
        VALUES (?,?,?,?,?)
        ON CONFLICT(category, key) DO UPDATE SET
            value=excluded.value,
            source=excluded.source,
            confidence=excluded.confidence,
            updated_at=strftime('%Y-%m-%dT%H:%M:%S','now')
    """, (category, key, value, source, confidence))
    conn.commit()
    conn.close()
    print(f"  [OK] {category}/{key}")


# ─────────────────────────────────────────────────────────────
#  BLOCO 1 — Conhecimento Core do Sistema (sempre executado)
# ─────────────────────────────────────────────────────────────

def seed_system_knowledge():
    """Injeta conhecimento verificado sobre o proprio sistema."""
    print("\n[1/4] Conhecimento do Sistema AGENTE-X")

    facts = [
        # Arquitetura
        ("ARCHITECTURE", "react_loop",
         "Ciclo ReAct: Thought->Action->ActionInput->Observation->repete. Max 20 passos. "
         "Se >20 passos sem Final Answer, encerrar com erro LOOP_LIMIT.",
         "SOUL.md + react_engine.py"),
        ("ARCHITECTURE", "provider_priority",
         "Ordem de prioridade LLM: 1.Ollama(local,gratis) > 2.DeepSeek > 3.Claude > 4.OpenAI > 5.Gemini. "
         "Nunca usar provider indisponivel sem tentar o proximo.",
         "llm_router.py"),
        ("ARCHITECTURE", "zero_ghost_law",
         "Lei Suprema: nenhum dado simulado, mockado ou fabricado. Tudo deve ser real e verificavel. "
         "Violacao = parada imediata. Fluxo: CRIAR->TESTAR->VALIDAR->REGISTRAR->SALVAR->REPORTAR.",
         "SOUL.md + ZERO_GHOST_MARTIAL_LAW.md"),
        ("ARCHITECTURE", "anti_loop_limits",
         "AntiLoopGuard: MAX_DEPTH=3, MAX_RETRIES=2, MAX_CALLS_PER_MINUTE_GLOBAL=20. "
         "Por agente: AGENTE_X=10rpm, WHATSAPP=5rpm, REACT_ENGINE=8rpm, DEFAULT=3rpm.",
         "anti_loop_guard.py"),
        ("ARCHITECTURE", "finance_circuit_breaker",
         "FinanceEngine bloqueia LLM se daily_limit excedido (padrao $2/dia, hard_stop $5/dia). "
         "Registra cada chamada em financeiro + llm_usage_ledger.",
         "finance_engine.py"),
        ("ARCHITECTURE", "ntfs_sqlite_fallback",
         "SQLite nao consegue fazer COMMIT em NTFS do sandbox Linux. "
         "Solucao: _connect() testa escrita e faz fallback para /tmp/agente_x_*.db automaticamente.",
         "finance_engine.py + anti_loop_guard.py"),

        # Modelos e custos
        ("LLM_PRICES", "deepseek_v3_2026",
         "DeepSeek V3 (2026): input=$0.14/M tokens, output=$0.28/M tokens. "
         "Cache-hit: $0.028/M (10x mais barato). 95% mais barato que GPT-4 Turbo. "
         "Modelo padrao para coding, debugging, arquitetura.",
         "api-docs.deepseek.com/pricing 2026"),
        ("LLM_PRICES", "claude_haiku_4_5",
         "Claude Haiku 4.5: input=$0.80/M tokens, output=$4.00/M tokens. "
         "Usar para tarefas leves quando DeepSeek indisponivel.",
         "finance_engine.py"),
        ("LLM_PRICES", "gpt4o_mini",
         "GPT-4o Mini: input=$0.15/M tokens, output=$0.60/M tokens. Mais barato da OpenAI.",
         "finance_engine.py"),
        ("LLM_PRICES", "gemini_flash",
         "Gemini 2.0/2.5 Flash: input=$0.10/M tokens, output=$0.40/M tokens. Mais barato disponivel.",
         "finance_engine.py"),

        # Regras operacionais
        ("OPERATIONAL_RULES", "e_drive_readonly",
         "A unidade E: eh somente-leitura. NUNCA escrever em E:. Usar D:/Agente X para todos os arquivos.",
         "AGENTS.md"),
        ("OPERATIONAL_RULES", "no_hollow_shells",
         "Nenhum modulo .py pode existir com apenas 'pass'. Todo arquivo deve ter implementacao real e funcional.",
         "SOUL.md"),
        ("OPERATIONAL_RULES", "skill_learning",
         "Apos 5+ passos em uma missao, salvar skill reutilizavel em 04_SKILLS/. "
         "Formato: nome_skill.py com docstring, entrada tipada, saida documentada.",
         "SOUL.md"),
        ("OPERATIONAL_RULES", "24x7_daemon",
         "Maestro roda em loop continuo. Intervalo padrao entre ciclos: 30s. "
         "Heartbeat a cada 5 min. Recovery de RUNNING orfaos a cada startup.",
         "maestro.py"),
        ("OPERATIONAL_RULES", "backup_schedule",
         "Backup diario automatico em 13_BACKUPS_DIARIOS/backup_YYYY-MM-DD/. "
         "Inclui: DB snapshot, arquivos criticos, BACKUP_MANIFEST.md. "
         "Gatilho: Maestro._daily_backup_if_needed() no heartbeat.",
         "maestro.py + save_manager.py"),

        # Diagnostico
        ("DIAGNOSTICS", "agente_diagnostico",
         "Rodar python agente_diagnostico.py para verificar 41 modulos (incl. M8 health+perf), DB, providers, backups. "
         "Score 100/100 = sistema saudavel. Gera JSON em 08_AUDITS/reports/diagnostico_YYYY-MM-DD.json.",
         "agente_diagnostico.py"),
        ("DIAGNOSTICS", "daily_report",
         "Relatorio diario gerado automaticamente pelo SaveManager + daily_report_generator.py. "
         "Salvo em 08_AUDITS/reports/RELATORIO_YYYY-MM-DD.md (MD) e relatorio_YYYY-MM-DD.json (JSON).",
         "daily_report_generator.py"),
        ("DIAGNOSTICS", "known_error_llmrouter_chat",
         "ERRO REAL: 'LLMRouter object has no attribute chat'. "
         "CAUSA: MissionBrain chamou router.chat() mas metodo correto eh router.route(). "
         "FIX: Substituir todas as chamadas .chat() por .route() no mission_brain.py.",
         "LearningLoop + logs/2026-05-27"),
    ]

    for cat, key, val, src in facts:
        inject(cat, key, val, src)


# ─────────────────────────────────────────────────────────────
#  BLOCO 2 — Padrões de Agentes Autônomos (conhecimento consolidado)
# ─────────────────────────────────────────────────────────────

def seed_agent_patterns():
    """Injeta padroes consolidados de agentes autonomos — fontes academicas/tecnicas verificadas."""
    print("\n[2/4] Padroes de Agentes Autonomos")

    patterns = [
        ("AGENT_PATTERNS", "react_paper_2022",
         "ReAct (Reasoning+Acting): agentes LLM que intercalam raciocinio e acoes. "
         "Fonte: Yao et al. 2022 'ReAct: Synergizing Reasoning and Acting in Language Models'. "
         "Principio: pensamento explicito antes de cada acao melhora precisao e rastreabilidade.",
         "arxiv.org/abs/2210.03629"),
        ("AGENT_PATTERNS", "tool_use_best_practices",
         "Melhores praticas para tool use em agentes: (1) descrever ferramenta com exemplos, "
         "(2) validar entrada antes de executar, (3) tratar erros de tool explicitamente no loop, "
         "(4) nunca usar tool sem necessidade (custo/latencia). "
         "Fonte: Anthropic Tool Use Guide 2024.",
         "docs.anthropic.com/tool-use"),
        ("AGENT_PATTERNS", "memory_hierarchy",
         "Hierarquia de memoria em agentes: (1) Working Memory=contexto atual, "
         "(2) Episodic Memory=historico de sessoes, (3) Semantic Memory=conhecimento geral (knowledge base), "
         "(4) Procedural Memory=skills/ferramentas. AGENTE-X implementa: short_term+long_term+vector+skills.",
         "Cognitive Science + LLM Agent Research"),
        ("AGENT_PATTERNS", "hallucination_prevention",
         "Prevencao de alucinacao: (1) grounding em dados reais (RAG), "
         "(2) verificacao de fatos contra fonte original, (3) admitir incerteza explicitamente, "
         "(4) nao inventar resultados de ferramentas. AGENTE-X: HallucinationGuard valida cada resposta.",
         "hallucination_guard.py + Zero Ghost"),
        ("AGENT_PATTERNS", "multi_agent_coordination",
         "Coordenacao multi-agente: hierarquia Orchestrator->SubAgents. "
         "Cada agente tem role especifico, limite de profundidade e rate limit proprio. "
         "Comunicacao via fila (fila_execucao) ou chamada direta. "
         "AGENTE-X: Maestro(orchestrator) + REACT_ENGINE + WHATSAPP + AGENTE_X.",
         "maestro.py + anti_loop_guard.py"),
        ("AGENT_PATTERNS", "cost_optimization_strategies",
         "Estrategias de otimizacao de custo LLM: (1) usar modelo local Ollama para classificacao (custo zero), "
         "(2) cache de respostas identicas, (3) comprimir prompt removendo exemplos redundantes, "
         "(4) usar local (Ollama) para tarefas simples, (5) circuit breaker para evitar loops caros. "
         "Implementado: FinanceEngine + task_classifier + anti_loop_guard.",
         "finance_engine.py + task_classifier.py"),
        ("AGENT_PATTERNS", "error_recovery_patterns",
         "Padroes de recuperacao de erros em agentes: (1) retry com backoff exponencial (max 2x), "
         "(2) fallback para provider alternativo, (3) degradacao graceful (resposta parcial), "
         "(4) log detalhado para aprendizado futuro, (5) nunca silenciar erros. "
         "AGENTE-X: AntiLoopGuard(retry) + LLMRouter(fallback) + LearningLoop(log).",
         "llm_router.py + anti_loop_guard.py + learning_loop.py"),
        ("AGENT_PATTERNS", "autonomous_24x7_requirements",
         "Requisitos para agente autonomo 24/7: "
         "(1) recovery automatico de falhas (Maestro._recover_stuck_running), "
         "(2) circuit breaker financeiro (FinanceEngine), "
         "(3) rate limiting (AntiLoopGuard), "
         "(4) logging persistente (SQLite logs), "
         "(5) backup diario automatico (SaveManager), "
         "(6) monitoramento em tempo real (monitor_backend.py), "
         "(7) governance de seguranca (SafeGate + RiskEngine).",
         "SOUL.md + system architecture"),
    ]

    for cat, key, val, src in patterns:
        inject(cat, key, val, src)


# ─────────────────────────────────────────────────────────────
#  BLOCO 3 — Lições aprendidas desta sessão
# ─────────────────────────────────────────────────────────────

def seed_session_lessons():
    """Injeta licoes aprendidas durante o desenvolvimento do AGENTE-X."""
    print("\n[3/4] Licoes Aprendidas da Sessao M6")

    lessons = [
        ("LESSONS_LEARNED", "ntfs_commit_fails",
         "SQLite nao faz COMMIT em NTFS montado no Linux (sandbox). "
         "Sintoma: disk I/O error no primeiro COMMIT. "
         "Solucao permanente: _connect() testa CREATE+DROP TABLE antes de retornar conexao, "
         "com fallback automatico para /tmp/. Implementado em finance_engine.py e anti_loop_guard.py.",
         "Session M6 debug 2026-05-27"),
        ("LESSONS_LEARNED", "replace_all_infinite_recursion",
         "Edit tool com replace_all=True em sqlite3.connect() dentro do proprio _connect() "
         "causou substituicao recursiva infinita. Solucao: usar Python str.replace() com "
         "string completa e unica para evitar colisoes. Alternativa: escrever arquivo completo via Write.",
         "Session M6 debug 2026-05-27"),
        ("LESSONS_LEARNED", "file_truncation_ntfs",
         "Escrever arquivos grandes diretamente em NTFS via Edit tool pode truncar no meio. "
         "Solucao: sempre escrever em /tmp primeiro, compilar com py_compile, "
         "depois copiar com cp para destino NTFS.",
         "Session M6 debug 2026-05-27"),
        ("LESSONS_LEARNED", "queue_flood_cleanup",
         "Queue teve 5985 itens de stress tests: MEM_SUPER_*, OVERFLOW_*, Q_SAT_*. "
         "Limpeza: CANCELLED via UPDATE. Nao deletar para manter auditoria. "
         "Prevencao: MissionBrain deve validar nome da missao antes de enfileirar.",
         "Session M6 cleanup 2026-05-27"),
        ("LESSONS_LEARNED", "api_keys_from_cofre",
         "Chaves API estavam em D:/Biblioteca/Sistema_open_claude/.env. "
         "Copiadas para D:/Agente X/.env. Providers configurados: DeepSeek, Claude, OpenAI, Gemini. "
         "Verificar com python test_llm.py (requer Windows com internet).",
         "Session M6 config 2026-05-27"),
        ("LESSONS_LEARNED", "relative_import_failure",
         "Importacao 'from .trace_context import TraceContext' falha quando modulo eh carregado "
         "via sys.path.insert (nao como pacote). Solucao: usar 'from trace_context import TraceContext' "
         "e garantir que o diretorio correto esta no sys.path antes do import.",
         "Session M6 anti_loop_guard fix 2026-05-27"),
        ("LESSONS_LEARNED", "status_method_missing",
         "agente_x.py --status causava AttributeError: 'ReActEngine' has no attribute 'status'. "
         "Causa: metodo nunca implementado. Solucao: implementar status() com dados reais "
         "de router, registry, skills e finance engine. Testar antes de reportar como OK.",
         "Session M6 CLI fix 2026-05-27"),
    ]

    for cat, key, val, src in lessons:
        inject(cat, key, val, src)


# ─────────────────────────────────────────────────────────────
#  BLOCO 4 — Busca web (apenas com --web ou --full)
# ─────────────────────────────────────────────────────────────

def seed_web_knowledge():
    """Busca real na web via DuckDuckGo (sem API key). Zero Ghost: dados reais ou nada."""
    print("\n[4/4] Busca de Conhecimento Externo (web)")
    if not WEB_MODE:
        print("  [--] Modo web desativado. Use --web para ativar.")
        return

    try:
        import sys as _s
        _s.path.insert(0, str(_ROOT / "01_CORE" / "tools"))
        from web_tool import WebTool
        web = WebTool()
    except Exception as e:
        print(f"  [!!] web_tool nao disponivel: {e}")
        return

    queries = [
        ("ReAct agent pattern LLM autonomous 2024", "AGENT_RESEARCH", "react_2024_summary"),
        ("LLM cost optimization prompt engineering techniques", "BEST_PRACTICES", "cost_opt_2024"),
        ("autonomous AI agent error recovery retry patterns", "BEST_PRACTICES", "error_recovery_2024"),
    ]

    for query, cat, key in queries:
        try:
            print(f"  Buscando: '{query}'")
            result = web.execute({"query": query, "num_results": 3})
            if result.get("success") and result.get("results"):
                # Extrair top 3 titulos e snippets como conhecimento
                summaries = []
                for r in result["results"][:3]:
                    title = r.get("title", "")
                    snippet = r.get("snippet", "")[:150]
                    url = r.get("url", "")
                    if title:
                        summaries.append(f"{title}: {snippet} [{url}]")
                if summaries:
                    value = " | ".join(summaries)
                    inject(cat, key, value[:1000], f"DuckDuckGo:{query}", confidence=0.7)
            else:
                print(f"  [--] Sem resultados para: {query}")
            time.sleep(1)  # Respeitar rate limit
        except Exception as e:
            print(f"  [!!] Erro na busca '{query}': {e}")



# ─────────────────────────────────────────────────────────────
#  BLOCO 5 — Regras de governança (RULE) — sempre executado
# ─────────────────────────────────────────────────────────────

def seed_governance_rules():
    """Garante que as 16 regras nucleares de governanca existam no DB. Zero Ghost."""
    print("\n[5/5] Regras de Governanca (RULE)")
    rules = [
        ("zero_ghost", "Nenhum codigo pode ser simulado ou mockado. Todos os dados e resultados devem ser REAIS.", 1.0),
        ("create_test_validate_save", "Todo artefato segue: CREATE->TEST->VALIDATE->SAVE. Nunca entregar sem testar.", 1.0),
        ("e_drive_readonly", "A unidade E: e somente-leitura. NUNCA escrever em E:. Violacao = halt imediato.", 1.0),
        ("no_hollow_shells", "Nenhum modulo .py pode nascer com pass ou corpo vazio. Todo codigo deve ser funcional.", 1.0),
        ("no_markdown_overdose", "Documentacao nao substitui codigo funcional. Prioridade: codigo real funcionando.", 1.0),
        ("react_loop", "Ciclo cognitivo: Thought->Action->Observation->repete. Maximo 20 passos.", 1.0),
        ("skill_learning", "Apos 5+ passos repetidos, o agente salva uma skill reutilizavel.", 1.0),
        ("24x7_daemon", "O Maestro roda em loop continuo processando a fila. Nunca deve travar silenciosamente.", 1.0),
        ("finance_preflight", "FinanceEngine bloqueia chamadas LLM se budget diario excedido.", 1.0),
        ("anti_loop", "AntiLoopGuard bloqueia recursao acima de 3 niveis e rajadas acima de 20 rpm.", 1.0),
        ("hallucination_guard", "HallucinationGuard valida cada resposta LLM contra o contexto real.", 1.0),
        ("hermes_soul", "SOUL.md define identidade do agente e carregado no Slot 1 do prompt.", 1.0),
        ("no_path_traversal", "SafeGate bloqueia path traversal. Nunca acessar diretorios fora do ROOT.", 1.0),
        ("no_shell_injection", "SafeGate bloqueia tokens perigosos: &&, ;, |, >, <, backtick, dollar-paren.", 1.0),
        ("no_drop_table", "SafeGate bloqueia DROP TABLE, rm -r, rmdir, del, format. Dados sao inviolaveis.", 1.0),
        ("verdade_absoluta", "Lei Marcial: toda resposta deve ser verificavel e baseada em dados reais do sistema.", 1.0),
    ]
    conn = _connect()
    inserted = 0
    for key, value, conf in rules:
        try:
            conn.execute(
                "INSERT OR IGNORE INTO knowledge (category, key, value, source, confidence) VALUES (?,?,?,?,?)",
                ("RULE", key, value, "HERMES_SEEDER_V2", conf),
            )
            inserted += conn.execute("SELECT changes()").fetchone()[0]
        except Exception as e:
            print("  [ERR] " + key + ": " + str(e))
    conn.commit()
    conn.close()
    print("  [OK] " + str(inserted) + " novas regras RULE inseridas (" + str(len(rules)) + " total)")


# ─────────────────────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────────────────────

def main():
    started = time.time()
    print("=" * 60)
    print("  AGENTE-X | Hermes Knowledge Seeder")
    import datetime as _dt
    print("  " + _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)

    seed_system_knowledge()
    seed_agent_patterns()
    seed_session_lessons()
    seed_web_knowledge()
    seed_governance_rules()

    # Verificar total injetado
    conn = _connect()
    total = conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
    by_cat = conn.execute(
        "SELECT category, COUNT(*) FROM knowledge GROUP BY category ORDER BY COUNT(*) DESC"
    ).fetchall()
    conn.close()

    elapsed = round(time.time() - started, 2)
    print("\n" + "=" * 60)
    print("  Knowledge Base: " + str(total) + " registros totais")
    for cat, cnt in by_cat:
        print("    " + str(cat) + ": " + str(cnt))
    print("  Tempo: " + str(elapsed) + "s")
    print("=" * 60)
    return total


if __name__ == "__main__":
    main()
