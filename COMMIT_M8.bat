@echo off
REM ============================================================
REM  AGENTE-X | COMMIT M8 — Health Monitor + Performance Tracker
REM  Execute no Windows apos COMMIT_M7.bat
REM  Data: 2026-05-28
REM ============================================================

cd /d "%~dp0"

echo ============================================================
echo   AGENTE-X ^| Git Commit M8 — Observability Engine
echo ============================================================

REM --- Criar pasta 05_HEALTH se nao existir ---
if not exist "05_HEALTH" mkdir 05_HEALTH

REM --- Adicionar novos modulos M8 ---
echo.
echo [1/4] Adicionando modulos M8...
git add 05_HEALTH/health_monitor.py
git add 05_HEALTH/performance_tracker.py

REM --- Adicionar modulos atualizados ---
echo.
echo [2/4] Adicionando modulos atualizados...
git add 03_RUNTIME/maestro.py
git add 04_SKILLS/hermes_knowledge_seeder.py
git add 01_CORE/mission_engine/rollback_engine.py
git add agente_diagnostico.py
git add setup_agente_x.py
git add COMMIT_M8.bat

REM --- Adicionar auditorias e reports M8 ---
echo.
echo [3/4] Adicionando reports de performance...
git add 08_AUDITS/performance/ 2>nul
git add 08_AUDITS/reports/RELATORIO_2026-05-28.md 2>nul
git add 08_AUDITS/reports/diagnostico_2026-05-28.json 2>nul
git add .gitignore

REM --- Commit ---
echo.
echo [4/4] Realizando commit M8...
git commit -m "feat(M8): health monitor, performance tracker, observability engine

Novos modulos (05_HEALTH/):
- health_monitor.py: alertas proativos em tempo real (error_spike,
  queue_stuck, budget_warning, backup_stale, missions_failed)
- performance_tracker.py: metricas reais por missao (tokens, custo USD,
  throughput, taxa de sucesso, provider top)

Integracoes no Maestro heartbeat (a cada 60s):
- _run_health_check(): executa HealthMonitor, persiste alertas criticos
- _cleanup_rate_stats(): limpa rate_limit_stats antigos via AntiLoopGuard

Melhorias M7->M8:
- hermes_knowledge_seeder.py: bloco 5 seed_governance_rules() — 16 regras
  RULE sempre preservadas em qualquer re-seed
- rollback_engine.py: sys.path corrigido para 01_CORE/mission_engine
- agente_diagnostico.py: lista expandida para 41 modulos (incl. M8)
- setup_agente_x.py: validacao dos 2 novos modulos M8

DB: Knowledge=79 registros | RULE=16 | QUEUED=0 | Score=100/100"

echo.
echo ============================================================
echo   Commit M8 concluido!
echo   Para subir: git push origin main
echo   Health check: python 05_HEALTH/health_monitor.py
echo   Performance:  python 05_HEALTH/performance_tracker.py
echo ============================================================
pause
