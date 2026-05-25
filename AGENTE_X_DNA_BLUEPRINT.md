# 🧬 DNA BLUEPRINT DO AGENTE-X

**Baseado na Mineração Forense (MISSÃO 002)**
**Data:** 2026-05-24

Este blueprint define as estruturas reais, funcionais e maduras encontradas nos projetos antigos que comporão a fundação (DNA) do AGENTE-X, rejeitando rigorosamente as simulações e os códigos "fantasmas".

---

## 🏗️ 1. ARQUITETURA RECOMENDADA

A arquitetura do AGENTE-X deve seguir a matriz 14-Core implantada na Fundação V1, preenchida pela lógica comprovada extraída dos seguintes herdeiros de sucesso:

### A. O Motor de Orquestração (Herança: SISTEMA OPEN CLAUDE)
- **Por que?** Possuía runtime real, ausência de mocks (score 9/10) e persistência verdadeira em SQLite (`.db`/`.ldb`).
- **O que absorver:**
  - `AGENTES`: Isolamento rígido de papéis.
  - `MEMORIA`: Lógica real de persistência associada ao banco de dados e não a dumps JSON "dummies".
  - `ORQUESTRADOR`: O script de execução de fluxo contínuo.

### B. A Governança e Validação (Herança: PHANDORA)
- **Por que?** Arquitetura organizacional e taxonômica impecável (RULES, WORKFLOWS, SKILLS, CONTAINERS).
- **O que absorver:**
  - `Truth Validator`: A ideia conceitual do validador de verdades e do `Evidence Collector`, que serão **reescritos do zero** (já que as versões antigas estavam infestadas de stubs).
  - O sistema de zero-trust gates, onde nenhuma ferramenta avança sem validação.

### C. A Interface e o Workspace (Herança: ANTIGRAVITY)
- **Por que?** Alta densidade de componentes visuais reais.
- **O que absorver:**
  - A lógica de UX e o modelo de interação do usuário.
  - O visual rico, podando de forma sumária todo o background fake que simulava telemetrias imaginárias.

### D. Ferramenta Local e Routing (Herança: OPENCLAW / SISTEMA ONE)
- **Por que?** Conceito valioso de roteamento de intenções de forma local.
- **O que absorver:** Apenas a arquitetura em diagrama de eventos e ciclo de vida de ferramentas conectadas ao disco do Diretor. O código em si (altamente mockado) não será importado.

---

## ⚖️ 2. AS 5 REGRAS DE CONTENÇÃO DO NOVO DNA (O QUE NÃO REPETIR)

Para o AGENTE-X manter sua integridade "Zero Ghost", instaura-se o banimento vitalício de:
1. **Cascas de Arquivo (Hollow Shells):** Nenhum módulo `.py` ou `.js` pode nascer apenas com `pass`. Se a lógica não está pronta para teste, o arquivo não deve ser salvo.
2. **Hardcoded Metrics e Telemetria Falsa:** Nada de variáveis como `trust_score = 99` chumbadas no código (tática encontrada no Sistema One). Relatórios refletirão 100% da verdade computada em logs autênticos.
3. **Mocks de Banco de Dados:** A memória do AGENTE-X usará conectores físicos reais desde a sua fundação.
4. **Markdown Overdose:** A engenharia não será afogada por 150 arquivos `.md` de planejamento enquanto o código sangra. CREATE → TEST → VALIDATE → SAVE.
5. **Cópia Frankenstein:** Projetos legados NÃO devem ser arrastados para as pastas do AGENTE-X. Eles servirão apenas como bibliotecas de pesquisa; as engrenagens limpas serão portadas função a função.

---

## 🎯 3. DIRETRIZES DE ABSORÇÃO

A extração deve ser iniciada com a migração cirúrgica dos runtimes validados do *Sistema Open Claude* para preencher as camadas vitais do `01_CORE` e `02_MEMORY` do AGENTE-X.
