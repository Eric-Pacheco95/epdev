@echo off
REM Jarvis Session Cleanup -- Task Scheduler wrapper
REM Kills claude.exe processes older than 8 hours to prevent session accumulation.
REM Safe to run while current sessions are active -- only targets stale processes.

cd /d "C:\Users\ericp\Github\epdev"

if not exist "data\logs" mkdir "data\logs"

for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set LOGDATE=%%I
set LOGFILE=data\logs\session_cleanup_%LOGDATE%.log

echo [%date% %time%] Session cleanup starting >> "%LOGFILE%" 2>&1
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\ericp\Github\epdev\tools\scripts\session_cleanup.ps1" >> "%LOGFILE%" 2>&1
echo [%date% %time%] Session cleanup complete (exit code: %ERRORLEVEL%) >> "%LOGFILE%" 2>&1
