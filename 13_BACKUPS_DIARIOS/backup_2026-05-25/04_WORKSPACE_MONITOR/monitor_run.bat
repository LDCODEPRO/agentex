@echo off
echo === AGENTE-X | Monitor Backend M6.2.1 ===
echo.
cd /d "D:\Agente X\04_WORKSPACE_MONITOR"

REM Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado. Instale Python 3.10+
    pause
    exit /b 1
)

echo [OK] Iniciando backend na porta 5050...
echo [OK] Abra monitor1_workspace.html no navegador
echo [OK] Ctrl+C para encerrar
echo.
python monitor_backend.py
pause
