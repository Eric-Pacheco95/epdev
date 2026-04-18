@echo off
REM Jarvis TELOS Introspection -- Task Scheduler wrapper
REM Runs daily (or on-demand). Analyzes TELOS vs signal evidence.
REM Uses claude -p (Claude Max subscription, no API key needed).
REM Env vars (SLACK_BOT_TOKEN) inherit from user env for optional Slack posting.

cd /d "C:\Users\ericp\Github\epdev"

REM Create log directory if missing
if not exist "data\logs" mkdir "data\logs"

REM Log file: one per day, append
set LOGDATE=%DATE%
set LOGFILE=data\logs\autoresearch_%LOGDATE%.log

REM Suspend check -- exits non-zero if watchdog has suspended this producer
"C:\Users\ericp\AppData\Local\Programs\Python\Python312\python.exe" tools\scripts\check_suspend.py jarvis_autoresearch >> "%LOGFILE%" 2>&1
if %ERRORLEVEL% EQU 3 exit /b 0

echo [%date% %time%] TELOS introspection starting >> "%LOGFILE%" 2>&1
"C:\Users\ericp\AppData\Local\Programs\Python\Python312\python.exe" tools\scripts\self_diagnose_wrapper.py -- "C:\Users\ericp\AppData\Local\Programs\Python\Python312\python.exe" tools\scripts\jarvis_autoresearch.py >> "%LOGFILE%" 2>&1
echo [%date% %time%] TELOS introspection complete (exit code: %ERRORLEVEL%) >> "%LOGFILE%" 2>&1
