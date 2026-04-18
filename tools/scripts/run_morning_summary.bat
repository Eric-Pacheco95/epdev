@echo off
REM Jarvis Morning Summary -- posts overnight work summary to #jarvis-decisions
REM Schedule: daily at 10am via Task Scheduler (\Jarvis\JarvisMorningSummary)

cd /d C:\Users\ericp\Github\epdev

set PYTHONPATH=C:\Users\ericp\Github\epdev
set JARVIS_SESSION_TYPE=autonomous

set LOGDATE=%DATE%

C:\Users\ericp\AppData\Local\Programs\Python\Python312\python.exe tools\scripts\morning_summary.py >> data\logs\morning_summary_%LOGDATE%.log 2>&1
