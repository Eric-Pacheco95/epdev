@echo off
REM Jarvis TELOS Introspection -- Task Scheduler wrapper
REM Runs daily (or on-demand). Analyzes TELOS vs signal evidence.
REM Uses claude -p (Claude Max subscription, no API key needed).
REM Env vars (SLACK_BOT_TOKEN) inherit from user env for optional Slack posting.

cd /d "C:\Users\ericp\Github\epdev"

REM Create log directory if missing
if not exist "data\logs" mkdir "data\logs"

REM Log file: one per day, append
for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set LOGDATE=%%I
set LOGFILE=data\logs\autoresearch_%LOGDATE%.log

echo [%date% %time%] TELOS introspection starting >> "%LOGFILE%" 2>&1
"C:\Users\ericp\AppData\Local\Programs\Python\Python312\python.exe" tools\scripts\self_diagnose_wrapper.py -- "C:\Users\ericp\AppData\Local\Programs\Python\Python312\python.exe" tools\scripts\jarvis_autoresearch.py >> "%LOGFILE%" 2>&1
echo [%date% %time%] TELOS introspection complete (exit code: %ERRORLEVEL%) >> "%LOGFILE%" 2>&1
