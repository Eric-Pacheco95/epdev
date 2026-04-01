@echo off
REM Jarvis FTS Index Update -- runs daily at 3am via Task Scheduler
REM Incremental update of jarvis_index.db from all data sources

set REPO_ROOT=C:\Users\ericp\Github\epdev
set PYTHON=C:\Users\ericp\AppData\Local\Programs\Python\Python312\python.exe
set LOG_DIR=%REPO_ROOT%\data\logs
for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set LOGDATE=%%I
set LOG_FILE=%LOG_DIR%\index_update_%LOGDATE%.log

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

echo [%date% %time%] Index update starting >> "%LOG_FILE%"

cd /d "%REPO_ROOT%"
"%PYTHON%" tools\scripts\jarvis_index.py update >> "%LOG_FILE%" 2>&1

if %ERRORLEVEL% EQU 0 (
    echo [%date% %time%] Index update completed successfully >> "%LOG_FILE%"
) else (
    echo [%date% %time%] Index update FAILED with exit code %ERRORLEVEL% >> "%LOG_FILE%"
)
