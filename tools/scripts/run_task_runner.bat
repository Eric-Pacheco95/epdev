@echo off
REM Jarvis Autonomous Task Runner -- POC
REM Reads tasklist, classifies tasks, executes automatable ones, posts summary.
REM Runs via Windows Task Scheduler every 4 hours.
REM Constitutional rules enforced: no TELOS writes, no git push, no secrets, no external mutations.

cd /d "C:\Users\ericp\Github\epdev"

REM Create log directory if missing
if not exist "data\logs" mkdir "data\logs"

REM Log file: one per day, append
set LOGDATE=%DATE%
set LOGFILE=data\logs\task_runner_%LOGDATE%.log

echo [%date% %time%] Task runner starting >> "%LOGFILE%" 2>&1

"C:\Users\ericp\.local\bin\claude.exe" -p "You are Jarvis running as an autonomous task runner. Read orchestration/tasklist.md and identify unchecked tasks (lines matching '- [ ]'). For EACH unchecked task, classify it: AUTO: Task can be completed right now without human input. Examples: run /synthesize-signals, run /security-audit, generate /research briefs, run /vitals, update steering rules (draft only). BLOCKED: Task requires human decision, physical action (install software, configure device), secret input, or external service setup. Tag with reason. DRAFT: Task can be partially completed -- write the output but leave unchecked for human review. Rules (NON-NEGOTIABLE): - Never modify TELOS identity files (memory/work/telos/) - Never run git push or git commit - Never modify CLAUDE.md steering rules directly (draft to memory/work/jarvis/task_runner_drafts/) - Never touch secrets, .env files, or credentials - Never post to Slack #general - Write all drafts to memory/work/jarvis/task_runner_drafts/ (create dir if needed) - Maximum 3 AUTO tasks per run (prevent runaway) - Log everything you do to memory/work/jarvis/task_runner_log.md (append, timestamped) Execute up to 3 AUTO tasks. For each: run the skill, verify the output, log the result. For BLOCKED tasks: append to task_runner_log.md with the reason. For DRAFT tasks: write the draft, log it. After all work, write a one-paragraph summary to memory/work/jarvis/task_runner_log.md with: tasks classified, tasks completed, tasks blocked, tasks drafted. Do NOT mark any tasklist checkboxes -- only the human session marks items complete after review." >> "%LOGFILE%" 2>&1

echo [%date% %time%] Task runner complete (exit code: %ERRORLEVEL%) >> "%LOGFILE%" 2>&1
