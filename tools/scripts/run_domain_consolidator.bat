@echo off
REM Jarvis Domain Knowledge Consolidator -- Task Scheduler wrapper
REM Runs weekly (Sunday 5:00am). Synthesizes domain knowledge articles
REM into _context.md and sub-domain files. Outputs go to a git worktree;
REM no auto-commit -- Eric reviews and runs --commit to accept.
REM Env vars (SLACK_BOT_TOKEN, ANTHROPIC_API_KEY) inherit from user environment.

cd /d "C:\Users\ericp\Github\epdev"

REM Create log directory if missing
if not exist "data\logs" mkdir "data\logs"

REM Log file: one per day, append
set LOGDATE=%DATE%
set LOGFILE=data\logs\domain_consolidator_%LOGDATE%.log

echo [%date% %time%] Domain Knowledge Consolidator starting >> "%LOGFILE%" 2>&1
"C:\Users\ericp\AppData\Local\Programs\Python\Python312\python.exe" tools\scripts\domain_knowledge_consolidator.py --autonomous >> "%LOGFILE%" 2>&1
set "RC=%ERRORLEVEL%"
echo [%date% %time%] Domain Knowledge Consolidator complete (exit code: %RC%) >> "%LOGFILE%" 2>&1
exit /b %RC%
