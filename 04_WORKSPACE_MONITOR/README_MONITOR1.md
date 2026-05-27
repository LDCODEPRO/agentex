# AGENTE-X | MONITOR 1 WORKSPACE

Esta pasta contém o Front-End inicial (V1) do painel de monitoramento do Agente-X.

## Arquivos
- `monitor1_workspace.html`: Estrutura de layout (Top, Left, Center, Right, Bottom).
- `monitor1_workspace.css`: Sistema de design focado em estética "Deep Dark" (Codex/Antigravity), com badges de Truth Governance (`REAL`, `UNAVAILABLE`).
- `monitor1_workspace.js`: Controlador de estado. Tenta realizar requisições ao backend de integração do AGENTE-X.

## Governança (Regra Zero Ghost)
Como não há um servidor backend real-time ainda escutando a porta para prover os status de Git, SQLite e Filas, a interface permanecerá com a marcação **UNAVAILABLE** em quase todos os componentes dinâmicos (Git, Chat, Métricas).

Isso não é um erro, é o **Design Determinado** de não forjar sucesso em métricas não conectadas.

## Como Executar
Basta abrir o arquivo `monitor1_workspace.html` em qualquer navegador moderno.
