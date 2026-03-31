@echo off
REM Jarvis Event Rotation — runs monthly, 1st at 3:00 AM
REM Summarizes + compresses old event JSONL files

cd /d C:\Users\ericp\Github\epdev
C:\Users\ericp\AppData\Local\Programs\Python\Python312\python.exe tools\scripts\rotate_events.py --execute >> data\logs\event_rotation.log 2>&1
