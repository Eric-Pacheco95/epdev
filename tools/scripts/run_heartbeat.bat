@echo off
REM Jarvis ISC Engine Heartbeat -- Task Scheduler wrapper
REM Runs heartbeat with logging. Called by Windows Task Scheduler every 60 min.
REM Env vars (SLACK_BOT_TOKEN, NTFY_TOPIC) inherit from user environment.

cd /d "C:\Users\ericp\Github\epdev"

REM Create log directory if missing
if not exist "data\logs" mkdir "data\logs"

REM Log file: one per day, append (locale-safe date via PowerShell)
set LOGDATE=%DATE%
set LOGFILE=data\logs\heartbeat_%LOGDATE%.log

REM Track worst exit code across all sub-tasks. Last sub-task's echo would
REM otherwise clobber %ERRORLEVEL% to 0 even if an earlier sub-task failed,
REM letting Task Scheduler report "success" on a partially-failed heartbeat.
set "WORST_RC=0"

REM Costs aggregator (PhaseC1) -- runs before heartbeat so json_field collectors read fresh data
echo [%date% %time%] Costs aggregator starting >> "%LOGFILE%" 2>&1
"C:\Users\ericp\AppData\Local\Programs\Python\Python312\python.exe" tools\scripts\costs_aggregator.py >> "%LOGFILE%" 2>&1
set "RC=%ERRORLEVEL%"
if %RC% NEQ 0 set "WORST_RC=%RC%"
echo [%date% %time%] Costs aggregator complete (exit code: %RC%) >> "%LOGFILE%" 2>&1

echo [%date% %time%] Heartbeat run starting >> "%LOGFILE%" 2>&1
"C:\Users\ericp\AppData\Local\Programs\Python\Python312\python.exe" tools\scripts\self_diagnose_wrapper.py -- "C:\Users\ericp\AppData\Local\Programs\Python\Python312\python.exe" tools\scripts\jarvis_heartbeat.py --quiet >> "%LOGFILE%" 2>&1
set "RC=%ERRORLEVEL%"
if %RC% NEQ 0 set "WORST_RC=%RC%"
echo [%date% %time%] Heartbeat run complete (exit code: %RC%) >> "%LOGFILE%" 2>&1

REM Knowledge Index incremental update (keeps search index fresh)
echo [%date% %time%] Knowledge index update starting >> "%LOGFILE%" 2>&1
"C:\Users\ericp\AppData\Local\Programs\Python\Python312\python.exe" tools\scripts\jarvis_index.py update >> "%LOGFILE%" 2>&1
set "RC=%ERRORLEVEL%"
if %RC% NEQ 0 set "WORST_RC=%RC%"
echo [%date% %time%] Knowledge index update complete (exit code: %RC%) >> "%LOGFILE%" 2>&1

REM Crypto-bot SENSE collector (Phase A -- read-only API poll + dead-man's switch)
echo [%date% %time%] Crypto-bot collector starting >> "%LOGFILE%" 2>&1
"C:\Users\ericp\AppData\Local\Programs\Python\Python312\python.exe" tools\scripts\crypto_bot_collector.py >> "%LOGFILE%" 2>&1
set "RC=%ERRORLEVEL%"
if %RC% NEQ 0 set "WORST_RC=%RC%"
echo [%date% %time%] Crypto-bot collector complete (exit code: %RC%) >> "%LOGFILE%" 2>&1

REM Log rotation (gzip old events, enforce retention policy)
echo [%date% %time%] Log rotation starting >> "%LOGFILE%" 2>&1
"C:\Users\ericp\AppData\Local\Programs\Python\Python312\python.exe" tools\scripts\rotate_events.py --execute >> "%LOGFILE%" 2>&1
set "RC=%ERRORLEVEL%"
if %RC% NEQ 0 set "WORST_RC=%RC%"
echo [%date% %time%] Log rotation complete (exit code: %RC%) >> "%LOGFILE%" 2>&1

exit /b %WORST_RC%
