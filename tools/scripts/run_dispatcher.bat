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
set LOGDATE=%DATE%
set LOGFILE=data\logs\dispatcher_%LOGDATE%.log

REM Suspend check -- exits non-zero if watchdog has suspended this producer
"C:\Users\ericp\AppData\Local\Programs\Python\Python312\python.exe" tools\scripts\check_suspend.py jarvis_dispatcher >> "%LOGFILE%" 2>&1
if %ERRORLEVEL% EQU 3 exit /b 0

REM Heartbeat -- touch before running so producer_recency measures "scheduler
REM fired" not "work produced". Idle-Is-Success runs still count as alive.
echo %date% %time% > "data\dispatcher_heartbeat.txt"

echo [%date% %time%] Dispatcher starting >> "%LOGFILE%" 2>&1
"C:\Users\ericp\AppData\Local\Programs\Python\Python312\python.exe" tools\scripts\self_diagnose_wrapper.py -- "C:\Users\ericp\AppData\Local\Programs\Python\Python312\python.exe" tools\scripts\jarvis_dispatcher.py >> "%LOGFILE%" 2>&1
set "RC=%ERRORLEVEL%"
echo [%date% %time%] Dispatcher complete (exit code: %RC%) >> "%LOGFILE%" 2>&1
exit /b %RC%
