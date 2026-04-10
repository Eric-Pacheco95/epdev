@echo off
REM Jarvis Session Cleanup -- Task Scheduler wrapper
REM Kills claude.exe processes older than 8 hours to prevent session accumulation.
REM Safe to run while current sessions are active -- only targets stale processes.

cd /d "C:\Users\ericp\Github\epdev"

if not exist "data\logs" mkdir "data\logs"

for /f %%I in ('C:\Users\ericp\AppData\Local\Programs\Python\Python312\python.exe C:\Users\ericp\Github\epdev\tools\scripts\today.py') do set LOGDATE=%%I
set LOGFILE=data\logs\session_cleanup_%LOGDATE%.log

echo [%date% %time%] Session cleanup starting >> "%LOGFILE%" 2>&1
"C:\Users\ericp\AppData\Local\Programs\Python\Python312\python.exe" "C:\Users\ericp\Github\epdev\tools\scripts\session_cleanup.py" >> "%LOGFILE%" 2>&1
echo [%date% %time%] Session cleanup complete (exit code: %ERRORLEVEL%) >> "%LOGFILE%" 2>&1
