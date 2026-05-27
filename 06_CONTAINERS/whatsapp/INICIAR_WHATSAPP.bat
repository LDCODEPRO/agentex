@echo off
echo ============================================
echo   AGENTE-X ^| WhatsApp M6
echo ============================================
echo.
echo [1/3] Instalando dependencias Node.js (primeira vez)...
cd /d "%~dp0"
call npm install
echo.
echo [2/3] Iniciando servidor WhatsApp (porta 3000)...
start "WhatsApp servidor.js" cmd /k "node servidor.js"
timeout /t 5 /nobreak > nul
echo.
echo [3/3] Iniciando AGENTE-X WhatsApp Bridge (porta 3001)...
start "WhatsApp Agent Python" cmd /k "python whatsapp_agent.py"
echo.
echo ============================================
echo   Escaneie o QR CODE com seu WhatsApp
echo   (aparece na janela servidor.js)
echo ============================================
pause
