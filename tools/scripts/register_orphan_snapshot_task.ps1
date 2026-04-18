# Register Jarvis-OrphanSnapshot as a Task Scheduler task.
# Run this ONCE (Admin not required -- uses RunLevel Limited per platform-specific.md rule).
# Uses S4U logon -- runs without requiring a user session.
#
# Success gate for orphan-prevention-oom PRD-1 Phase 4.

$ErrorActionPreference = "Stop"

$taskName = "Jarvis-OrphanSnapshot"
$taskPath = "\Jarvis\"  # trailing slash required -- Windows stores tasks under \Jarvis\ and the readback CIM query is literal
$batPath = "C:\Users\ericp\Github\epdev\tools\scripts\run_orphan_snapshot.bat"
$workDir = "C:\Users\ericp\Github\epdev"
$userId = $env:USERNAME

# Remove existing task if present (idempotent re-registration)
$existing = Get-ScheduledTask -TaskPath $taskPath -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing) {
    $existing | Unregister-ScheduledTask -Confirm:$false -ErrorAction Stop
    Write-Host "Removed existing $taskPath\$taskName"
}

$action = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument "/c `"$batPath`"" `
    -WorkingDirectory $workDir

# Daily 00:05 trigger
$trigger = New-ScheduledTaskTrigger -Daily -At "00:05"

# S4U + Limited: runs without active user session, no admin elevation needed
$principal = New-ScheduledTaskPrincipal `
    -UserId $userId `
    -LogonType S4U `
    -RunLevel Limited

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
    -Force `
    -ErrorAction Stop | Out-Null

# Verification readback -- confirm mutation actually took effect
$readback = Get-ScheduledTask -TaskPath $taskPath -TaskName $taskName -ErrorAction Stop
if ($readback.Principal.LogonType -ne "S4U") {
    throw "Verification failed: LogonType is $($readback.Principal.LogonType), expected S4U"
}
if ($readback.Principal.RunLevel -ne "Limited") {
    throw "Verification failed: RunLevel is $($readback.Principal.RunLevel), expected Limited"
}

Write-Host "Registered + verified: $taskPath\$taskName (S4U + Limited, daily 00:05)"
Write-Host ("State: {0}, Next run: {1}" -f $readback.State, (Get-ScheduledTaskInfo -TaskPath $taskPath -TaskName $taskName).NextRunTime)
