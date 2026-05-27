# AGENTE-X — Regras do Projeto

Este arquivo e carregado automaticamente em cada sessao do AGENTE-X.
Equivalente ao AGENTS.md do Hermes Agent — regras de contexto do projeto.

## Estrutura de Diretorios

```
D:\Agente X\
├── 00_GOVERNANCE/RULES/    → safe_gate.py, risk_engine.py
├── 01_CORE/orchestrator/   → llm_router.py, tool_registry.py, react_engine.py
├── 01_CORE/tools/          → file_tool.py, shell_tool.py, memory_tool.py, web_tool.py
├── 02_MEMORY/long_term/    → memory_manager.py, db_init.py (SQLite)
├── 02_MEMORY/short_term/   → context_manager.py, MEMORY.md
├── 02_MEMORY/vector_memory/→ chroma_manager.py (ChromaDB)
├── 03_RUNTIME/             → maestro.py (daemon 24/7)
├── 04_SKILLS/learned/      → skills auto-geradas em JSON
├── 07_MISSIONS/            → relatorios de missao em markdown
├── 08_AUDITS/              → relatorios executivos
├── 09_LOGS/                → logs de execucao
├── 12_CONFIG/              → SOUL.md, director_profile.py
└── agente_x.py             → entry point principal
```

## Convencoes de Codigo

- Python 3.10+ (f-strings, type hints onde claro)
- Zero emoji em codigo — usar [OK], [ERRO], [AVISO]
- Zero hollow shells — todo metodo tem logica real
- Imports relativos com fallback: try/except ImportError para compatibilidade
- Logs em 09_LOGS/ via logging padrao Python
- Banco SQLite em 02_MEMORY/agente_x.db

## Regras de Missao

- Missoes numeradas: M1, M2, M3... (prefixo padrao)
- Relatorio obrigatorio apos cada missao em 07_MISSIONS/
- Status validos: PENDING, IN_PROGRESS, DONE, FAILED
- Salvar em 3 camadas apos missao: disco + GitHub + Obsidian

## Ferramentas Disponiveis

- file_tool: operacoes em arquivos do projeto (read, write, list, exists)
- shell_tool: comandos shell seguros (validados por safe_gate)
- memory_tool: SQLite + ChromaDB (save, recall, search, log)
- web_tool: fetch de URLs e busca DuckDuckGo

## Restricoes Absolutas

- NUNCA escrever em E: (unidade somente-leitura)
- NUNCA executar: rm -rf, rmdir /s, del /f, format, DROP TABLE
- NUNCA inventar observacoes ou resultados de ferramentas
- NUNCA criar arquivos com dados mockados ou simulados
