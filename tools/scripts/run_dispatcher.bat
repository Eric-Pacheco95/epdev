@echo off
REM Jarvis Autonomous Dispatcher -- Task Scheduler wrapper
REM Runs after overnight runner (5am daily). Picks one task from backlog,
REM executes in worktree, verifies ISC, notifies via Slack.
REM Wrapped in self_diagnose_wrapper for failure capture.

cd /d "C:\Users\ericp\Github\epdev"

REM Mark session as autonomous (activates P0 security validators)
set JARVIS_SESSION_TYPE=autonomous

REM Create log directory if missing
if not exist "data\logs" mkdir "data\logs"

REM Log file: one per day, append
for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set LOGDATE=%%I
set LOGFILE=data\logs\dispatcher_%LOGDATE%.log

echo [%date% %time%] Dispatcher starting >> "%LOGFILE%" 2>&1
"C:\Users\ericp\AppData\Local\Programs\Python\Python312\python.exe" tools\scripts\self_diagnose_wrapper.py -- "C:\Users\ericp\AppData\Local\Programs\Python\Python312\python.exe" tools\scripts\jarvis_dispatcher.py >> "%LOGFILE%" 2>&1
echo [%date% %time%] Dispatcher complete (exit code: %ERRORLEVEL%) >> "%LOGFILE%" 2>&1
