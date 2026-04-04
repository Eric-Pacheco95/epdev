@echo off
REM Jarvis Research Producer -- Task Scheduler wrapper
REM Runs daily (suggested: 3am -- before overnight runner at 4am).
REM Checks research_topics.json, injects overdue research tasks into backlog.
REM No LLM calls -- pure SENSE layer, completes in seconds.

cd /d "C:\Users\ericp\Github\epdev"

if not exist "data\logs" mkdir "data\logs"

for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set LOGDATE=%%I
set LOGFILE=data\logs\research_producer_%LOGDATE%.log

echo [%date% %time%] Research producer starting >> "%LOGFILE%" 2>&1
"C:\Users\ericp\AppData\Local\Programs\Python\Python312\python.exe" tools\scripts\research_producer.py >> "%LOGFILE%" 2>&1
echo [%date% %time%] Research producer complete (exit code: %ERRORLEVEL%) >> "%LOGFILE%" 2>&1
