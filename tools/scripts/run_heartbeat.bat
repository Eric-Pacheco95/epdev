@echo off
REM Jarvis ISC Engine Heartbeat -- Task Scheduler wrapper
REM Runs heartbeat with logging. Called by Windows Task Scheduler every 60 min.
REM Env vars (SLACK_BOT_TOKEN, NTFY_TOPIC) inherit from user environment.

cd /d "C:\Users\ericp\Github\epdev"

REM Create log directory if missing
if not exist "data\logs" mkdir "data\logs"

REM Log file: one per day, append (locale-safe date via PowerShell)
for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set LOGDATE=%%I
set LOGFILE=data\logs\heartbeat_%LOGDATE%.log

echo [%date% %time%] Heartbeat run starting >> "%LOGFILE%" 2>&1
"C:\Users\ericp\AppData\Local\Programs\Python\Python312\python.exe" tools\scripts\jarvis_heartbeat.py >> "%LOGFILE%" 2>&1
echo [%date% %time%] Heartbeat run complete (exit code: %ERRORLEVEL%) >> "%LOGFILE%" 2>&1

REM Knowledge Index incremental update (keeps search index fresh)
echo [%date% %time%] Knowledge index update starting >> "%LOGFILE%" 2>&1
"C:\Users\ericp\AppData\Local\Programs\Python\Python312\python.exe" tools\scripts\jarvis_index.py update >> "%LOGFILE%" 2>&1
echo [%date% %time%] Knowledge index update complete (exit code: %ERRORLEVEL%) >> "%LOGFILE%" 2>&1

REM Log rotation (gzip old events, enforce retention policy)
echo [%date% %time%] Log rotation starting >> "%LOGFILE%" 2>&1
"C:\Users\ericp\AppData\Local\Programs\Python\Python312\python.exe" tools\scripts\rotate_events.py --execute >> "%LOGFILE%" 2>&1
echo [%date% %time%] Log rotation complete (exit code: %ERRORLEVEL%) >> "%LOGFILE%" 2>&1
