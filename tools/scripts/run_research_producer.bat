@echo off
REM Jarvis Research Producer -- Task Scheduler wrapper
REM Runs daily (suggested: 3am -- before overnight runner at 4am).
REM Checks research_topics.json, injects overdue research tasks into backlog.
REM No LLM calls -- pure SENSE layer, completes in seconds.

cd /d "C:\Users\ericp\Github\epdev"

if not exist "data\logs" mkdir "data\logs"

set LOGDATE=%DATE%
set LOGFILE=data\logs\research_producer_%LOGDATE%.log

REM Suspend check -- exits non-zero if watchdog has suspended this producer
"C:\Users\ericp\AppData\Local\Programs\Python\Python312\python.exe" tools\scripts\check_suspend.py research_producer >> "%LOGFILE%" 2>&1
if %ERRORLEVEL% EQU 3 exit /b 0

echo [%date% %time%] Research producer starting >> "%LOGFILE%" 2>&1
"C:\Users\ericp\AppData\Local\Programs\Python\Python312\python.exe" tools\scripts\research_producer.py >> "%LOGFILE%" 2>&1
set "RC=%ERRORLEVEL%"
echo [%date% %time%] Research producer complete (exit code: %RC%) >> "%LOGFILE%" 2>&1
exit /b %RC%
