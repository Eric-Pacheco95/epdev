# Register Moralis stream health monitor as a Task Scheduler task.
# Run this script ONCE from an elevated (Run as Administrator) PowerShell.
# Uses S4U logon -- runs without requiring a user session (headless, no stored password).
#
# Purpose: primary signal for Moralis CU overage prevention. Polls stream status
# hourly; alerts #epdev if status != "active"; auto-pauses stream on error
# dwell > 1h. Counterpart to the local webhook CU counter in dashboard/app.py.

$ErrorActionPreference = "Stop"

$taskName = "MoralisStreamMonitor"
$taskPath = "\Jarvis"
$batPath = "C:\Users\ericp\Github\epdev\tools\scripts\run_moralis_monitor.bat"
$workDir = "C:\Users\ericp\Github\epdev"
$userId = $env:USERNAME

# Remove existing task if present
Get-ScheduledTask -TaskPath $taskPath -TaskName $taskName -ErrorAction SilentlyContinue |
    Unregister-ScheduledTask -Confirm:$false -ErrorAction SilentlyContinue

$action = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument "/c `"$batPath`"" `
    -WorkingDirectory $workDir

# Hourly trigger; starts 10 minutes from now to avoid the top-of-hour storm.
# -RepetitionDuration capped at 25 years (Task Scheduler XML rejects TimeSpan::MaxValue).
$startAt = (Get-Date).AddMinutes(10)
$trigger = New-ScheduledTaskTrigger -Once -At $startAt `
    -RepetitionInterval (New-TimeSpan -Hours 1) `
    -RepetitionDuration (New-TimeSpan -Days 9125)

# S4U: runs without active user session, no stored password
$principal = New-ScheduledTaskPrincipal `
    -UserId $userId `
    -LogonType S4U `
    -RunLevel Highest

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew

Register-ScheduledTask `
    -TaskName $taskName `
    -TaskPath $taskPath `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Force

Write-Host "Registered: $taskPath\$taskName (S4U, hourly, 5min limit)"
Write-Host "First run: $startAt"
Write-Host "Verify: Get-ScheduledTask -TaskPath '$taskPath' -TaskName '$taskName' | Select-Object -ExpandProperty Triggers"
