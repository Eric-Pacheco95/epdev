# Register Jarvis Domain Knowledge Consolidator as a Task Scheduler task.
# Run this script ONCE from an elevated (Run as Administrator) PowerShell.
# Uses S4U logon -- runs without requiring a user session (headless, no stored password).

$ErrorActionPreference = "Stop"

$taskName = "DomainKnowledgeConsolidator"
$taskPath = "\Jarvis"
$batPath = "C:\Users\ericp\Github\epdev\tools\scripts\run_domain_consolidator.bat"
$workDir = "C:\Users\ericp\Github\epdev"
$userId = $env:USERNAME

# Remove existing task if present
Get-ScheduledTask -TaskPath $taskPath -TaskName $taskName -ErrorAction SilentlyContinue |
    Unregister-ScheduledTask -Confirm:$false -ErrorAction SilentlyContinue

$action = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument "/c `"$batPath`"" `
    -WorkingDirectory $workDir

# Weekly Sunday 5:00am trigger
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At "05:00AM"

# S4U: runs without active user session, no stored password
$principal = New-ScheduledTaskPrincipal `
    -UserId $userId `
    -LogonType S4U `
    -RunLevel Highest

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
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

Write-Host "Registered: $taskPath\$taskName (S4U, Sunday 5am, 30min limit)"
Write-Host "Verify: Get-ScheduledTask -TaskPath '$taskPath' -TaskName '$taskName' | Select-Object -ExpandProperty Principal | Select-Object LogonType"
