@echo off
REM ============================================================
REM  AGENTE-X | COMMIT M7 — Diagnostics, Reports, HERMES Seeds
REM  Execute este arquivo UMA VEZ no Windows para commitar M7
REM  Data: 2026-05-27
REM ============================================================

cd /d "%~dp0"

echo ============================================================
echo   AGENTE-X ^| Git Commit M7
echo ============================================================

REM --- Atualizar .gitignore para excluir arquivos temporarios ---
echo.
echo [1/5] Atualizando .gitignore...
findstr /c:".fuse_hidden" .gitignore >nul 2>&1
if errorlevel 1 (
    echo. >> .gitignore
    echo # SQLite WAL / FUSE temporarios >> .gitignore
    echo *.db-shm >> .gitignore
    echo *.db-wal >> .gitignore
    echo *.db-journal >> .gitignore
    echo .fuse_hidden* >> .gitignore
    echo [OK] .gitignore atualizado
) else (
    echo [OK] .gitignore ja atualizado
)

REM --- Adicionar novos modulos Python ---
echo.
echo [2/5] Adicionando novos modulos Python...
git add agente_diagnostico.py
git add agente_x.py
git add setup_agente_x.py
git add 04_SKILLS/hermes_knowledge_seeder.py
git add 10_GITHUB/daily_report_generator.py
git add 10_GITHUB/save_manager.py
git add 13_BACKUPS_DIARIOS/BACKUP_DIARIO.bat

REM --- Adicionar modulos modificados M7 ---
echo.
echo [3/5] Adicionando modulos modificados M7...
git add 01_CORE/orchestrator/learning_loop.py
git add 01_CORE/orchestrator/react_engine.py
git add 01_CORE/mission_engine/mission_templates.py
git add 01_CORE/mission_engine/mission_brain.py
git add 01_CORE/mission_engine/rollback_engine.py
git add 03_RUNTIME/maestro.py

REM --- Adicionar monitor e workspace ---
echo.
echo [4/5] Adicionando monitor e auditorias...
git add 04_WORKSPACE_MONITOR/monitor1_workspace.html
git add 04_WORKSPACE_MONITOR/monitor1_workspace.css
git add 04_WORKSPACE_MONITOR/monitor1_workspace.js
git add 04_WORKSPACE_MONITOR/monitor_backend.py
git add 04_WORKSPACE_MONITOR/monitor_run.bat
git add 08_AUDITS/reports/RELATORIO_2026-05-27.md
git add 08_AUDITS/reports/diagnostico_2026-05-27.json
git add 08_AUDITS/reports/relatorio_2026-05-27.json
git add .gitignore

REM --- Commit ---
echo.
echo [5/5] Realizando commit...
git commit -m "feat(M7): diagnostico 39 modulos, daily reports, HERMES knowledge seeder

Novos modulos:
- agente_diagnostico.py: 39 modulos, score 100/100, JSON output
- daily_report_generator.py: relatorio MD+JSON diario (Zero Ghost)
- hermes_knowledge_seeder.py: base de conhecimento 20->62 registros

Modulos melhorados:
- learning_loop.py: heuristicas reais, 10 regex patterns (sem simulacao)
- mission_templates.py: usa LLM real, fallback estatico documentado
- mission_brain.py: correcao router.chat()->router.route()
- rollback_engine.py: sem comentarios 'fase 5', retorna dict real
- maestro.py: fix _ROOT.parent->_ROOT (bug critico), seed 6h
- save_manager.py: integra daily_report em cada backup
- agente_x.py: flag --diagnose adicionada

Score: 39/39 modulos OK | Knowledge: 62 registros | FAILED: 0"

echo.
echo ============================================================
echo   Commit M7 concluido!
echo   Proximos passos:
echo     git push origin main
echo     python agente_x.py --diagnose
echo ============================================================
pause
