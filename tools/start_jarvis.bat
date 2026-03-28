@echo off
title Jarvis Launcher
cd /d "C:\Users\ericp\Github\epdev"

echo Starting Jarvis background services...

REM Start Slack Inbox Poller
start "Jarvis INBOX POLLER" cmd /k "python tools\scripts\slack_poller.py"

REM Start Slack Voice Processor
start "Jarvis VOICE PROCESSOR" cmd /k "python tools\scripts\slack_voice_processor.py"

REM Run heartbeat once on startup then let Task Scheduler handle recurring runs
python tools\scripts\jarvis_heartbeat.py

echo.
echo Jarvis services launched.
echo   - INBOX POLLER:    polls #jarvis-inbox every 60s, replies in thread
echo   - VOICE PROCESSOR: polls #jarvis-voice every 60s, extracts signals
echo   - HEARTBEAT:       ran once on startup (Task Scheduler handles daily runs)
echo.
