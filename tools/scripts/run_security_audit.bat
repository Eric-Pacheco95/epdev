@echo off
REM Jarvis Security Audit -- Task Scheduler wrapper
REM Runs /security-audit via claude -p daily. Posts summary to #epdev Slack.
REM Must NOT run while an active Claude Code session is open (subprocess contention).

cd /d "C:\Users\ericp\Github\epdev"

if not exist "data\logs" mkdir "data\logs"

set LOGDATE=%DATE%
set LOGFILE=data\logs\security_audit_%LOGDATE%.log

echo [%date% %time%] Security audit starting >> "%LOGFILE%" 2>&1
claude -p "Run /security-audit on this repo. After the audit completes, post a concise summary to #epdev Slack channel (C0ANZKK12CD) via Slack MCP. Format: 'Security audit [date]: N findings (breakdown). Top: [highest]. Risk: [level].' If clean: 'Security audit [date]: Clean - 0 findings. Risk: Low.' Always post to Slack." >> "%LOGFILE%" 2>&1
set "RC=%ERRORLEVEL%"
echo [%date% %time%] Security audit complete (exit code: %RC%) >> "%LOGFILE%" 2>&1
exit /b %RC%
