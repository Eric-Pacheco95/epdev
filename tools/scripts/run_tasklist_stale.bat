@echo off
REM Jarvis Tasklist Stale Detector -- Task Scheduler wrapper
REM Checks for stale tasks weekly. Posts findings to #epdev Slack.

cd /d "C:\Users\ericp\Github\epdev"

if not exist "data\logs" mkdir "data\logs"

for /f %%I in ('C:\Users\ericp\AppData\Local\Programs\Python\Python312\python.exe C:\Users\ericp\Github\epdev\tools\scripts\today.py') do set LOGDATE=%%I
set LOGFILE=data\logs\tasklist_stale_%LOGDATE%.log

echo [%date% %time%] Tasklist stale check starting >> "%LOGFILE%" 2>&1
claude -p "Read orchestration/tasklist.md. Identify: (1) unchecked tasks that have not been updated in 14+ days (check git log for last modification of the task line), (2) checked items with 'pending' or 'awaiting' in their description (the built-not-validated anti-pattern), (3) any phase marked ACTIVE with zero progress in 14+ days. Post a summary to #epdev Slack (C0ANZKK12CD): 'Tasklist check [date]: N stale tasks, M built-but-pending items, K stalled phases.' List the top 3 most concerning items. If everything is healthy: 'Tasklist check [date]: All clear - no stale items detected.'" >> "%LOGFILE%" 2>&1
echo [%date% %time%] Tasklist stale check complete (exit code: %ERRORLEVEL%) >> "%LOGFILE%" 2>&1
