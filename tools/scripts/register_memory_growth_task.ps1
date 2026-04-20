# register_memory_growth_task.ps1
#
# IMPORTANT: Run this script ELEVATED (right-click PowerShell -> "Run as Administrator").
# S4U tasks require admin for first registration (2026-04-18 learning).
#
# Registers a weekly Windows Task Scheduler job that logs the Jarvis memory
# file count to data/memory_growth.jsonl every Monday at 08:00.

$TaskName    = "Jarvis_MemoryGrowth_Weekly"
$RepoRoot    = "C:\Users\ericp\Github\epdev"
$ScriptPath  = "$RepoRoot\tools\scripts\log_memory_growth.py"
$PythonExe   = (Get-Command python -ErrorAction Stop).Source

if (-not (Test-Path $ScriptPath)) {
    Write-Error "Script not found: $ScriptPath"
    exit 1
}

$Action = New-ScheduledTaskAction `
    -Execute $PythonExe `
    -Argument "`"$ScriptPath`"" `
    -WorkingDirectory $RepoRoot

$Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At "08:00"

$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
    -MultipleInstances IgnoreNew `
    -StartWhenAvailable

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Phase 6A.1 Signal 3 -- weekly Jarvis memory file count logger" `
    -RunLevel Highest `
    -Force

Write-Host ""
Write-Host "Registered: $TaskName"
Write-Host "Schedule  : Every Monday at 08:00"
Write-Host "Output    : $RepoRoot\data\memory_growth.jsonl"
Write-Host ""
Write-Host "To test immediately (no elevation needed after registration):"
Write-Host "  Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "  # or:"
Write-Host "  python `"$ScriptPath`""
