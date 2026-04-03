@echo off
REM Jarvis Paradigm Health Monitor -- Task Scheduler wrapper
REM Runs daily at 1:55pm ET (5 min before overnight runner at 2pm).
REM SENSE layer: measures all 10 paradigm metrics, no LLM calls, <30 seconds.
REM Posts to Slack #epdev only when alerts exist.

cd /d "C:\Users\ericp\Github\epdev"

REM Create log directory if missing
if not exist "data\logs" mkdir "data\logs"

REM Log file: one per day, append (locale-safe date via PowerShell)
for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set LOGDATE=%%I
set LOGFILE=data\logs\paradigm_health_%LOGDATE%.log

echo [%date% %time%] Paradigm health check starting >> "%LOGFILE%" 2>&1
"C:\Users\ericp\AppData\Local\Programs\Python\Python312\python.exe" tools\scripts\paradigm_health.py >> "%LOGFILE%" 2>&1
echo [%date% %time%] Paradigm health check complete (exit code: %ERRORLEVEL%) >> "%LOGFILE%" 2>&1
