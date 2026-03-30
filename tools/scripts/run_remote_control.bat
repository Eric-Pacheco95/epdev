@echo off
REM Persistent claude remote-control wrapper with auto-restart
REM Run this in a standalone CMD window (not inside Claude Code)

:loop
echo [%date% %time%] Starting claude remote-control...
claude remote-control
echo [%date% %time%] remote-control exited (code %ERRORLEVEL%). Restarting in 10 seconds...
timeout /t 10 /nobreak >nul
goto loop
