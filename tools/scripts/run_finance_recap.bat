@echo off
REM Jarvis Finance Recap -- Task Scheduler wrapper
REM Posts nightly position recap + AI analysis to Slack #finance.
REM Runs at 9:30 PM ET (after market close + settlement).

cd /d "C:\Users\ericp\Github\epdev"

REM Create log directory if missing
if not exist "data\logs" mkdir "data\logs"

REM Log file: one per day, append
set LOGDATE=%DATE%
set LOGFILE=data\logs\finance_recap_%LOGDATE%.log

echo [%date% %time%] Finance recap starting >> "%LOGFILE%" 2>&1
"C:\Users\ericp\AppData\Local\Programs\Python\Python312\python.exe" tools\scripts\finance_recap.py --analyze >> "%LOGFILE%" 2>&1
set "RC=%ERRORLEVEL%"
echo [%date% %time%] Finance recap complete (exit code: %RC%) >> "%LOGFILE%" 2>&1
exit /b %RC%
