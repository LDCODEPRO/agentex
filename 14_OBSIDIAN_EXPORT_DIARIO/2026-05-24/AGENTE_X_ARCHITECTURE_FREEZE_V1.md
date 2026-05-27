# AGENTE-X: ARCHITECTURE FREEZE V1

**DATA DO CONGELAMENTO:** 2026-05-24
**MISSÃO:** 003
**AUTORIDADE:** DIRETOR (LUIZ CIPOLARI)

Este documento atesta a arquitetura base do AGENTE-X aprovada e congelada antes de qualquer implementação de código, originada exclusivamente de DNA validado sem fantasias. Nenhuma decisão estrutural poderá violar os dogmas deste documento sem autorização prévia.

---

## 1. IDENTIDADE E PAPEL OFICIAL
O AGENTE-X atua como um **Sistema Operacional Agêntico 24/7 & Engenheiro de Projetos**.
*   **Não é um Chatbot:** É um orquestrador (Maestro) com persistência em disco que processa filas de tarefas.
*   **Não sofre de fadiga cognitiva:** Reduz loops iterativos processando missões em background.
*   **Tem autonomia restrita:** Age livremente dentro do limite de suas `Skills` nas missões designadas, mas depende do Diretor para aprovações sensíveis (`HIGH RISK`) e alterações do seu próprio núcleo.

## 2. HIERARQUIA DE SISTEMA
A cadeia de comando inviolável é:
`DIRETOR` → `AGENTE-X (Maestro)` → `SUBAGENTES (Especialistas)` → `TOOLS / SKILLS` → `RUNTIME / FILESYSTEM`

*   **Diretor:** Define `Objetivos`, concede `Autorização` para `Risk Engine`.
*   **AGENTE-X (Maestro):** Planeja via DAG, delega para Subagentes ou ferramentas, consolida e escreve em Memória.
*   **Subagentes:** Invocados sob demanda com ciclo de vida descartável, apenas se uma `Skill` atômica não for suficiente.

## 3. CORE (NÚCLEO E DNA)
Destino das relíquias garimpadas na E:\:
*   **SAFE GATE:** `Evoluir`. Path raiz dinâmico. Age como última barreira do sistema de arquivos.
*   **RISK ENGINE:** `Evoluir`. Integração semântica adicionada ao controle por palavras-chave.
*   **HALLUCINATION GUARD:** `Refatorar`. Adoção de Embeddings ChromaDB ao invés de ratios ingênuos de strings.
*   **SINFONIA NEXUS:** `Evoluir`. Assume a postura de Orquestrador assíncrono (Mission Executor), sem a tralha das nomenclaturas antigas ("O_Baixador", etc.).
*   **LLM ROUTER SISTEMA_ONE:** `Importar Direto`. Assume controle total da decisão de modelos, priorizando health check, failover automático e controle estrito de `privacy_engine`.
*   **ZEUS CORE DB:** `Evoluir (Schema)`. Herdaremos apenas o DDL de tabelas como `missoes`, `behavioral_stability_log`, `cognitive_metrics`. O dado antigo (1 milhão de logs) será descartado.

## 4. SISTEMA DE MEMÓRIA (COGNITIVE LAYER)
*   **STM (Short Term Memory):** Limitada ao escopo do Runtime Context. Janela do LLM + Tabela SQLite `conversation_runtime` indexada por ID de Sessão.
*   **LTM (Long Term Memory):** ChromaDB persistido em `02_MEMORY/vector/`. Responsável pela busca RAG de documentação técnica e regras de governança.
*   **Mission & Executive Memory:** Tabela transacional em SQLite (`missoes`, `etapas`). Permite ao Diretor rastrear onde o sistema parou (ou falhou), com possibilidade real de `Rollback` do banco de dados do Agente.

## 5. MODELO DE ROTEAMENTO LLM (TIERING)
1.  **DeepSeek:** Codificação Pesada e Resolução de Problemas Críticos.
2.  **Gemini:** Processamento de Logs, Velocidade, Extratos e Summaries.
3.  **OpenAI (GPT-4o):** Validação de Arquitetura, Revisão e Depuração fina.
4.  **Claude:** Análise Forense, Tarefas complexas não-determinísticas.
5.  **Ollama (Local):** Privacidade Absoluta, Parsing de Arquivos `.env` e Senhas, Operação Offline de Failover.

## 6. PIPELINE DE EXECUÇÃO
1.  **Recepção:** Recebe ordem via CLI / Event Bus.
2.  **Governança:** O `Risk Engine` verifica se é Seguro, Revisão ou Bloqueado.
3.  **Planejamento:** O Maestro desmembra em DAG.
4.  **Execução:** Delegação assíncrona.
5.  **Validação:** `Safe Gate` defende o disco; Testes locais são rodados.
6.  **Persistência:** Gravado na Memória e gerado Report.
7.  **Backup:** Sincronização Obsidian & GitHub automática diária.

## 7. UX E COMUNICAÇÃO
Linguagem executiva: Relatórios limpos, sem "chatiness", sem invenções. O AGENTE-X operará prioritariamente através de painéis CLI/Markdown ou APIs RESTful limitadas, servindo como uma verdadeira interface máquina-para-Diretor.

## 8. STACK DE TECNOLOGIA
*   **Core:** Python 3.11+
*   **Relacional:** SQLite (Total soberania sobre disco local)
*   **Vetorial:** ChromaDB (Sem Cloud Vector DBs)
*   **Validação:** Pydantic
*   **Zero Frameworks desnecessários:** Flask/FastAPI serão incorporados apenas se e quando houver necessidade de UI externa. Inicialmente, o Agente operará via terminal nativo.
