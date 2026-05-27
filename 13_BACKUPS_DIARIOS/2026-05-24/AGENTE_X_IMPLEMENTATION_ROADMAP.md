# AGENTE-X: IMPLEMENTATION ROADMAP

**STATUS:** CONGELADO E PRONTO PARA AÇÃO

Este roadmap define as próximas missões atômicas, estruturadas cronologicamente para evitar dependências cíclicas e retrabalho. 

---

## 🛑 M1. SHIELD PROTOCOL (Ação Imediata)
**Foco:** Blindagem estrutural antes de qualquer código.
*   **Ação:** Criar `.gitignore` universal contendo `.env`, `.sqlite3` (para não sujar git), `__pycache__`.
*   **Ação:** Validar tracking do git.
*   **Ação:** Criar `D:\Agente X\.env` com placeholders (`SK-...`) limpos e seguros.

## 🛡️ M2. GOVERNANCE INJECTION
**Foco:** Transferir as regras de ouro e sistemas de restrição.
*   **Ação:** Importar e adaptar `E:\BIBLIOTECA_COMPLEXO_ZEUS\05_RULES\*.md` para `D:\Agente X\00_GOVERNANCE\RULES\`.
*   **Ação:** Importar e reescrever `safe_gate.py` (Mudar root fixo para path dinâmico do Agente X). Testar os 12 casos de bloqueio shell e path traversal.
*   **Ação:** Importar e refinar `risk_engine.py` como módulo básico.

## 🧠 M3. ROUTER & COGNITION UPLOAD
**Foco:** Dar cérebro ao sistema.
*   **Ação:** Importar todo o bloco do `SISTEMA_ONE\01_CORE\llm_router\` para `01_CORE\llm_router\`.
*   **Ação:** Fixar a política de roteamento (`routing_policy.py`) no padrão: DeepSeek, Gemini, OpenAI, Claude, Ollama.
*   **Ação:** Acoplar o motor ao arquivo de chaves blindado pelo Shield Protocol.
*   **Ação:** Testar `provider_health.py` chamando as APIs em tempo real.

## 💾 M4. MEMORY FOUNDATION
**Foco:** O hipocampo do AGENTE-X.
*   **Ação:** Criar schema SQL limpo baseado nas tabelas-alvo vitais identificadas do `zeus_core.db` antigo.
*   **Ação:** Inicializar o banco zerado `D:\Agente X\02_MEMORY\agente_x.db`.
*   **Ação:** Inicializar ChromaDB isolado em `02_MEMORY\vector\`.

## ⚙️ M5. THE MAESTRO BOOT (RUNTIME 24/7)
**Foco:** O loop infinito de execução e auto-heal.
*   **Ação:** Pegar o conceito do `Sinfonia Nexus` e criar o `mission_executor.py`.
*   **Ação:** Criar tabela `fila_execucao` no SQLite.
*   **Ação:** Desenvolver o *Watchdog* (Loop) rodando em background que consome a fila e despacha as ordens via Pydantic + Roteador LLM.
*   **Ação:** Realizar teste de crash (Mata o Python `kill -9` e liga de novo para provar o *Auto-Heal* recuperando o estado pendente no SQLite).

---

## MODO OPERANTE PARA TODAS AS FASES
*   Zero Ghost. Nenhuma implementação fantasma.
*   CREATE → TEST → VALIDATE → SAVE.
*   Somente o Diretor emite o OK para avançar as Missões (M1 a M5).
