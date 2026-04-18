@echo off
REM Jarvis Overnight Consolidation -- Task Scheduler wrapper
REM Runs after dispatcher + overnight runner complete (e.g., 6:30am).
REM Merges all overnight branches into jarvis/review-YYYY-MM-DD.
REM Wrapped in self_diagnose_wrapper for failure capture.

cd /d "C:\Users\ericp\Github\epdev"

REM Create log directory if missing
if not exist "data\logs" mkdir "data\logs"

REM Log file: one per day, append
set LOGDATE=%DATE%
set LOGFILE=data\logs\consolidate_%LOGDATE%.log

echo [%date% %time%] Consolidation starting >> "%LOGFILE%" 2>&1
"C:\Users\ericp\AppData\Local\Programs\Python\Python312\python.exe" tools\scripts\self_diagnose_wrapper.py -- "C:\Users\ericp\AppData\Local\Programs\Python\Python312\python.exe" tools\scripts\consolidate_overnight.py >> "%LOGFILE%" 2>&1
echo [%date% %time%] Consolidation complete (exit code: %ERRORLEVEL%) >> "%LOGFILE%" 2>&1
