@echo off
title Jarvis Launcher
cd /d "C:\Users\ericp\Github\epdev"

echo Starting Jarvis background services...

REM Suspend check -- skip INBOX POLLER if watchdog has suspended it
"C:\Users\ericp\AppData\Local\Programs\Python\Python312\python.exe" tools\scripts\check_suspend.py slack_poller
if %ERRORLEVEL% EQU 3 (
    echo   [SKIPPED] slack_poller is suspended -- not launching INBOX POLLER
    goto skip_inbox_poller
)

REM Start Slack Inbox Poller
start "Jarvis INBOX POLLER" cmd /k "python tools\scripts\slack_poller.py"

:skip_inbox_poller

REM Run heartbeat once on startup then let Task Scheduler handle recurring runs
python tools\scripts\jarvis_heartbeat.py

echo.
echo Jarvis services launched.
echo   - INBOX POLLER:    polls #jarvis-inbox every 60s, replies in thread
echo   - HEARTBEAT:       ran once on startup (Task Scheduler handles daily runs)
echo.
