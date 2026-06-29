@echo off
REM AGENTE-X | Backup Diario Automatico
REM Agendar no Windows Task Scheduler: diariamente as 02:00
REM Como agendar: abra "Agendador de Tarefas" do Windows e crie tarefa
REM   Disparador: Diario as 02:00
REM   Acao: iniciar programa: D:\Agente X\13_BACKUPS_DIARIOS\BACKUP_DIARIO.bat

cd /d "D:\Agente X"

echo [%date% %time%] Iniciando backup diario do AGENTE-X... >> 09_LOGS\backup_diario.log
python agente_x.py --save >> 09_LOGS\backup_diario.log 2>&1
echo [%date% %time%] Backup concluido. >> 09_LOGS\backup_diario.log
