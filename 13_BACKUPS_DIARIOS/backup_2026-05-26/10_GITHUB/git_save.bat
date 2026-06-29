@echo off
REM AGENTE-X | Git Save Script
REM Execute este arquivo para commitar e fazer push de todas as mudancas.
REM Duplo clique ou: cd "D:\Agente X\10_GITHUB" && git_save.bat

cd /d "D:\Agente X"

echo.
echo ================================================
echo   AGENTE-X ^| Git Save - Auto Commit + Push
echo ================================================

REM Remover lock se existir
IF EXIST ".git\index.lock" (
    echo [INFO] Removendo index.lock...
    del /f ".git\index.lock"
)

REM Verificar se e repositorio git
git rev-parse --git-dir >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERRO] Nao e um repositorio git. Execute: git init
    pause
    exit /b 1
)

REM Adicionar todos os arquivos
echo [1/3] git add -A ...
git add -A
IF %ERRORLEVEL% NEQ 0 (
    echo [ERRO] git add falhou.
    pause
    exit /b 1
)

REM Verificar se ha mudancas
git diff --cached --quiet
IF %ERRORLEVEL% EQU 0 (
    echo [OK] Nada para commitar - working tree limpa.
    goto :push
)

REM Commit com timestamp
FOR /F "tokens=1-3 delims=/ " %%a IN ('date /t') DO SET DATA=%%c-%%b-%%a
FOR /F "tokens=1-2 delims=: " %%a IN ('time /t') DO SET HORA=%%a:%%b
SET COMMIT_MSG=[AGENTE-X] Auto-save %DATA% %HORA% - Missoes M1-M5 concluidas

echo [2/3] git commit...
git commit -m "%COMMIT_MSG%"
IF %ERRORLEVEL% NEQ 0 (
    echo [ERRO] git commit falhou.
    pause
    exit /b 1
)
echo [OK] Commit realizado: %COMMIT_MSG%

:push
REM Push se tiver remote
echo [3/3] git push...
git remote -v | find "origin" >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    git push origin HEAD
    IF %ERRORLEVEL% EQU 0 (
        echo [OK] Push realizado com sucesso.
    ) ELSE (
        echo [AVISO] Push falhou - verifique conexao e credenciais.
        echo [INFO] Commit local foi salvo. Tente: git push origin HEAD
    )
) ELSE (
    echo [AVISO] Sem remote configurado. Commit local salvo.
    echo [INFO] Para configurar: git remote add origin https://github.com/SEU_USER/agente-x.git
)

echo.
echo ================================================
echo   Backup GitHub concluido!
echo   Execute tambem: python agente_x.py --save
echo   para backup disco local + Obsidian
echo ================================================
echo.
pause
