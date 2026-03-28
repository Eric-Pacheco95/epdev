@echo off
REM Jarvis Steering Rules Audit -- Task Scheduler wrapper
REM Runs /synthesize-signals + /update-steering-rules via claude -p weekly.
REM Posts proposed rules to #epdev Slack for Eric's review.

cd /d "C:\Users\ericp\Github\epdev"

if not exist "data\logs" mkdir "data\logs"

for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set LOGDATE=%%I
set LOGFILE=data\logs\steering_audit_%LOGDATE%.log

echo [%date% %time%] Steering audit starting >> "%LOGFILE%" 2>&1
claude -p "Check unprocessed signal count in memory/learning/signals/ (excluding processed/ subdir). If count >= 8, run /synthesize-signals first. Then run /update-steering-rules. Post a summary to #epdev Slack (C0ANZKK12CD): how many signals synthesized, how many rules proposed, and list each proposed rule in one line. If no new rules warranted, post 'Steering audit [date]: No new rules proposed. N signals reviewed.'" >> "%LOGFILE%" 2>&1
echo [%date% %time%] Steering audit complete (exit code: %ERRORLEVEL%) >> "%LOGFILE%" 2>&1
