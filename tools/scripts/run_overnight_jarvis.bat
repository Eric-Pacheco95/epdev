@echo off
REM Jarvis Overnight Self-Improvement -- Task Scheduler wrapper
REM Runs at 4am daily. Rotates through improvement dimensions.
REM Max 2 hours wall clock (enforced by Task Scheduler timeout).
REM Env vars (SLACK_BOT_TOKEN) inherit from user environment.

cd /d "C:\Users\ericp\Github\epdev"

REM Create log directory if missing
if not exist "data\logs" mkdir "data\logs"

REM Log file: one per day, append
for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set LOGDATE=%%I
set LOGFILE=data\logs\overnight_%LOGDATE%.log

echo [%date% %time%] Overnight self-improvement starting >> "%LOGFILE%" 2>&1
"C:\Users\ericp\AppData\Local\Programs\Python\Python312\python.exe" tools\scripts\self_diagnose_wrapper.py -- "C:\Users\ericp\AppData\Local\Programs\Python\Python312\python.exe" tools\scripts\overnight_runner.py >> "%LOGFILE%" 2>&1
echo [%date% %time%] Overnight self-improvement complete (exit code: %ERRORLEVEL%) >> "%LOGFILE%" 2>&1
