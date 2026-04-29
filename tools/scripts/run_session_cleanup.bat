@echo off
REM Jarvis Session Cleanup -- Task Scheduler wrapper
REM Kills claude.exe processes older than 8 hours to prevent session accumulation.
REM Safe to run while current sessions are active -- only targets stale processes.

cd /d "C:\Users\ericp\Github\epdev"

if not exist "data\logs" mkdir "data\logs"

set LOGDATE=%DATE%
set LOGFILE=data\logs\session_cleanup_%LOGDATE%.log

echo [%date% %time%] Session cleanup starting >> "%LOGFILE%" 2>&1
"C:\Users\ericp\AppData\Local\Programs\Python\Python312\python.exe" "C:\Users\ericp\Github\epdev\tools\scripts\session_cleanup.py" >> "%LOGFILE%" 2>&1
set "RC=%ERRORLEVEL%"
echo [%date% %time%] Session cleanup complete (exit code: %RC%) >> "%LOGFILE%" 2>&1
exit /b %RC%
