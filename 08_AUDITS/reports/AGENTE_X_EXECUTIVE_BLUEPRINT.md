# AGENTE-X: EXECUTIVE BLUEPRINT

**ESTADO:** APROVADO / CONGELADO

Este blueprint define a estrutura mental, operacional e cognitiva do AGENTE-X em linguagem técnica-executiva.

---

## A. O CÉREBRO: ARQUITETURA COGNITIVA
O AGENTE-X não é um Large Language Model (LLM) envelopado; ele é um orquestrador agêntico que consome múltiplos LLMs como "motores".

*   **Roteador de LLMs (Sistema One importado):**
    Uma camada inteligente que seleciona dinamicamente a API que executará o nó atual da missão. 
    *Exemplo: Tarefas pesadas vão para DeepSeek V4 Pro, resumos rápidos vão para Gemini, arquivos protegidos ativam o Privacy Engine que bloqueia a saída externa e usa o modelo Ollama 100% offline e local.*
*   **Hallucination Guard:**
    Ao receber respostas, o sistema compara a morfologia e a semântica gerada com a base documental (Vector Memory). Falso-positivos de claims são reprovados, gerando Retry automático sem intervenção humana.
*   **Risk Engine:**
    Analisa os prompts de intenção antes deles sequer iniciarem. Um Prompt de exclusão de arquivos entra na tag `HIGH_RISK`, é pausado pelo Maestro, notifica o Diretor na interface CLI/Dashboard e aguarda o `Approval Gate`.

## B. O CORAÇÃO: MOTOR 24/7 (SINFONIA NEXUS V2)
A base rítmica do sistema é o "Sinfonia Nexus", que agora será rebatizado para "Mission Executor" ou Maestro.
*   **Heartbeat Threading:** Uma thread leve em Python (watchdog) gira monitorando a tabela `fila_execucao` no SQLite.
*   **DAG (Directed Acyclic Graph):** Missões grandes são quebradas em subtarefas dependentes. A Tarefa 2 só roda se a Tarefa 1 registrar `status='concluido'` no banco.
*   **Auto-Heal:** Se o processo Python morrer brutalmente (queda de luz ou `kill -9`), ao religar, a thread carrega do SQLite as etapas que estavam marcadas `em_andamento`, transforma em `pendente_falha` e reexecuta com o histórico intacto.

## C. A ESTRUTURA CORPORAL: FILESYSTEM E GOVERNANÇA
O sistema herda a lógica implacável do "Zero Ghost".
*   **00_GOVERNANCE:** Onde reside o `Safe Gate`, `Risk Engine`, `.gitignore` universal e o cofre de segredos (`.env` local, não versionado).
*   **01_CORE:** O roteador LLM, a inteligência de prompt e a abstração do banco SQLite.
*   **02_MEMORY:** Banco SQLite (transacional), ChromaDB (Vectorial) e logs crus (`.jsonl`).
*   **03_WORKFLOWS:** "Fábricas" pré-programadas de execução contínua.
*   **04_SKILLS:** Ferramentas atômicas (escrever arquivo, ler API, rodar terminal).

## D. O ESQUELETO SOBERANO: BANCO DE DADOS
Sem dependência de MongoDB Atlas, Redis, ou serviços cloud externos.
*   **`zeus_core.db` (Remasterizado):** O banco do Agente conterá estritamente `missoes`, `conversation_runtime` (estado em andamento) e `behavioral_stability_log` (para métricas de sanidade mental da IA).
*   **ChromaDB Local:** O vector storage não precisa de conta na nuvem. A pasta local será montada em `02_MEMORY/vector` para guardar a memória enciclopédica (LTM).
