# AGENTE-X: SAFE IMPORT PLAN

**REFERÊNCIA:** MISSÃO 002.2
**DATA DA AUDITORIA:** 2026-05-24

O projeto herdará fragmentos de código vitais descobertos na `E:\`, mas para evitar a "Síndrome de Frankenstein" (caos, dependências mortas e falhas de segurança), o fluxo de importação obedecerá ao seguinte protocolo seguro e cirúrgico.

---

## 🛑 FASE 0: BLINDAGEM DO REPOSITÓRIO (RISCO CRÍTICO)
Identificamos que não existe `.gitignore` nativo protegendo os repositórios contra a publicação de chaves secretas no arquivo `.env`.

**Passos a executar na próxima missão ANTES de importar o código:**
1. Criar `D:\Agente X\.gitignore` contendo as proteções universais (`.env`, `__pycache__`, `*.sqlite3`, `logs/`, etc.).
2. Adicionar o `.gitignore` e comitar na branch `main`.
3. Validar se o git ignorou o arquivo. Somente após esta checagem o primeiro `.env` poderá ser criado em segurança para testes locais.

---

## 🏗️ FASE 1: IMPORTAÇÃO DA GOVERNANÇA CORE
1. Copiar `E:\BIBLIOTECA_COMPLEXO_ZEUS\05_RULES\*.md` para `D:\Agente X\00_GOVERNANCE\RULES\`.
2. Criar `D:\Agente X\00_GOVERNANCE\CONTAINERS\safe_gate.py` adaptado a partir do código do `E:\NIVEL 1\RESGATE\Nexus_Claude\Core\safe_gate.py`.
   * **Alteração Necessária:** Substituir a raiz de segurança `D:\DATASTORE\Nexus_Claude` para dinamicamente ler `D:\Agente X`.
3. Criar `D:\Agente X\00_GOVERNANCE\RULES\risk_engine.py` evoluindo o script de palavras-chave para o futuro.

---

## 🧠 FASE 2: IMPORTAÇÃO DO MOTOR LLM
A inteligência multi-agente será alimentada por um cluster sólido e validado de roteadores.
1. Copiar todo o conteúdo validado de `E:\SISTEMA_ONE\01_CORE\llm_router\` para `D:\Agente X\01_CORE\llm_router\`.
2. Fundir e sobrescrever a hierarquia de custos do `routing_policy.py` para fixar a ordem: 
   *(1) DeepSeek, (2) Gemini, (3) OpenAI, (4) Claude, (5) Ollama local*.
3. O `privacy_engine.py` validará secret keys.
4. O `provider_health.py` será testado nativamente pelo Diretor.

---

## ⚡ FASE 3: IMPORTAÇÃO DO ORQUESTRADOR
1. Criar `D:\Agente X\01_CORE\orchestrator\sinfonia_nexus_v2.py`.
2. Absorver as lógicas de `ThreadPoolExecutor`, `Pydantic` e DAG (grafos direcionados) do arquivo antigo.
3. Excluir TODA a tralha legado de telemetria ("o_baixador", "o_designer") para usar apenas as nomenclaturas das SKILLS e WORKFLOWS oficiais do AGENTE-X.

---

## 💾 FASE 4: CRIAÇÃO SOBERANA DA MEMÓRIA
1. **NÃO COPIAR** o arquivo massivo `zeus_core.db` (133MB com 1 milhão de logs mortos).
2. Criar um script SQL (`02_MEMORY\init_schema.sql`) extraindo os esquemas (DDL) das tabelas de ouro da mineração passada:
   - `missoes`
   - `memorias`
   - `behavioral_stability_log`
   - `cognitive_metrics`
3. Recriar os bancos de ChromaDB localmente apontando para a pasta local (`02_MEMORY/vector_memory/`).

---

## 📌 PRÓXIMA MISSÃO RECOMENDADA
> **MISSÃO 003 — SHIELD PROTOCOL & GOVERNANCE INJECTION**
> Executar a FASE 0 (Blindagem de Arquivos/Git) e a FASE 1 deste plano, integrando definitivamente o `safe_gate` e os arquivos de regras no AGENTE-X.
