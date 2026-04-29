@echo off
REM Jarvis-OrphanSnapshot -- Task Scheduler wrapper (00:05 daily)
REM Appends daily python.exe count to data/logs/orphan_python_snapshot.jsonl.
REM Success gate for orphan-prevention-oom PRD-1 Phase 4.
REM Intentionally zero subprocess-for-date -- uses %DATE% natively.

cd /d "C:\Users\ericp\Github\epdev"

if not exist "data\logs" mkdir "data\logs"

set LOGDATE=%DATE%
set LOGFILE=data\logs\orphan_snapshot_%LOGDATE%.log

echo [%date% %time%] Orphan snapshot starting >> "%LOGFILE%" 2>&1
"C:\Users\ericp\AppData\Local\Programs\Python\Python312\python.exe" tools\scripts\snapshot_orphan_python.py >> "%LOGFILE%" 2>&1
set "RC=%ERRORLEVEL%"
echo [%date% %time%] Orphan snapshot complete (exit %RC%) >> "%LOGFILE%" 2>&1
exit /b %RC%
