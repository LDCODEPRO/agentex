@echo off
echo === AGENTE-X | Commit M6 ===
cd /d "D:\Agente X"

REM Remover lock se existir
if exist ".git\index.lock" (
    del /f ".git\index.lock"
    echo [OK] index.lock removido
)

git add -A
git commit -m "M6: Absorver Biblioteca + WhatsApp + AntiLoop + HallucinationGuard + FinanceEngine - FinanceEngine (ZEUS): circuit breaker financeiro, dual ledger SQLite - TaskClassifier (SISTEMA_ONE): 14 tipos, standalone - HallucinationGuard (PHANDORA): validacao morfologica - hermes_core.py (Sistema_open_claude): SOUL+MEMORY+SKILLS dinamico - trace_context.py + anti_loop_guard.py (ZEUS) - M6 WhatsApp: servidor.js + whatsapp_agent.py - llm_router.py: AntiLoopGuard integrado no preflight - setup_agente_x.py: M1-M6, novas deps, novo schema - VALIDACAO: 29/29 OK, 0 erros"

echo.
echo === Commit concluido ===
pause
