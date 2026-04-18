@echo off
REM Jarvis Morning Feed -- Task Scheduler wrapper
REM Runs at 9am daily. Posts combined briefing to #epdev Slack.
REM Uses Anthropic API directly (no claude -p) to avoid session contention.
REM Env vars (ANTHROPIC_API_KEY, SLACK_BOT_TOKEN) inherit from user environment.

cd /d "C:\Users\ericp\Github\epdev"

REM Create log directory if missing
if not exist "data\logs" mkdir "data\logs"

REM Log file: one per day, append
set LOGDATE=%DATE%
set LOGFILE=data\logs\morning_feed_%LOGDATE%.log

echo [%date% %time%] Morning feed starting >> "%LOGFILE%" 2>&1
"C:\Users\ericp\AppData\Local\Programs\Python\Python312\python.exe" tools\scripts\self_diagnose_wrapper.py -- "C:\Users\ericp\AppData\Local\Programs\Python\Python312\python.exe" tools\scripts\morning_feed.py >> "%LOGFILE%" 2>&1
echo [%date% %time%] Morning feed complete (exit code: %ERRORLEVEL%) >> "%LOGFILE%" 2>&1
