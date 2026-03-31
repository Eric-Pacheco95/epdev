@echo off
REM Jarvis Heartbeat Rotation — runs monthly, 1st at 3:10 AM
REM Summarizes old entries into monthly JSON, keeps 30 days raw

cd /d C:\Users\ericp\Github\epdev
C:\Users\ericp\AppData\Local\Programs\Python\Python312\python.exe tools\scripts\rotate_heartbeat.py --execute >> data\logs\heartbeat_rotation.log 2>&1
