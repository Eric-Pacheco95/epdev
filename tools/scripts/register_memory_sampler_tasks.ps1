# Register Jarvis-MemorySampler-Night (2-min, 22:00-08:00) and
# Jarvis-MemorySampler-Day (10-min, 08:00-22:00) as Task Scheduler tasks.
#
# Run ONCE from an elevated PowerShell (Admin). S4U logon requires the caller
# to (re)grant "Log on as a batch job" to the target user; non-elevated runs
# return HRESULT 0x80070005 ("Access is denied") on Register-ScheduledTask
# even though the eventual runtime principal is S4U + Limited and needs no
# elevation itself.
#
# Success gate for memory-observability PRD-2 Phase 1 (FR-003).

$ErrorActionPreference = "Stop"

$taskPath = "\Jarvis\"  # trailing slash required -- readback CIM query is literal
$batPath = "C:\Users\ericp\Github\epdev\tools\scripts\run_memory_sampler.bat"
$workDir = "C:\Users\ericp\Github\epdev"
$userId = $env:USERNAME

function Register-SamplerTask {
    param(
        [Parameter(Mandatory)][string]$TaskName,
        [Parameter(Mandatory)][string]$StartAt,
        [Parameter(Mandatory)][int]$IntervalMinutes,
        [Parameter(Mandatory)][int]$DurationHours,
        [Parameter(Mandatory)][int]$DurationMinutes
    )

    $existing = Get-ScheduledTask -TaskPath $taskPath -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($existing) {
        $existing | Unregister-ScheduledTask -Confirm:$false -ErrorAction Stop
        Write-Host "Removed existing $taskPath$TaskName"
    }

    $action = New-ScheduledTaskAction `
        -Execute "cmd.exe" `
        -Argument "/c `"$batPath`"" `
        -WorkingDirectory $workDir

    # Daily trigger at StartAt, repeating every $IntervalMinutes for $DurationHours.
    # Repetition is attached from a throwaway -Once trigger because the -Daily
    # parameter set does not expose -RepetitionInterval directly.
    $trigger = New-ScheduledTaskTrigger -Daily -At $StartAt
    $durationSpan = New-TimeSpan -Hours $DurationHours -Minutes $DurationMinutes
    $repetition = (New-ScheduledTaskTrigger -Once -At $StartAt `
        -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes) `
        -RepetitionDuration $durationSpan).Repetition
    $trigger.Repetition = $repetition

    $principal = New-ScheduledTaskPrincipal `
        -UserId $userId `
        -LogonType S4U `
        -RunLevel Limited

    $settings = New-ScheduledTaskSettingsSet `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 2) `
        -StartWhenAvailable `
        -MultipleInstances IgnoreNew

    Register-ScheduledTask `
        -TaskName $TaskName `
        -TaskPath $taskPath `
        -Action $action `
        -Trigger $trigger `
        -Principal $principal `
        -Settings $settings `
        -Force `
        -ErrorAction Stop | Out-Null

    # Verification readback -- confirm mutation actually took effect.
    $readback = Get-ScheduledTask -TaskPath $taskPath -TaskName $TaskName -ErrorAction Stop
    if ($readback.Principal.LogonType -ne "S4U") {
        throw "Verification failed for ${TaskName}: LogonType is $($readback.Principal.LogonType), expected S4U"
    }
    if ($readback.Principal.RunLevel -ne "Limited") {
        throw "Verification failed for ${TaskName}: RunLevel is $($readback.Principal.RunLevel), expected Limited"
    }
    if ($readback.Settings.MultipleInstances -ne "IgnoreNew") {
        throw "Verification failed for ${TaskName}: MultipleInstances is $($readback.Settings.MultipleInstances), expected IgnoreNew"
    }
    $repInterval = $readback.Triggers[0].Repetition.Interval
    if (-not $repInterval) {
        throw "Verification failed for ${TaskName}: RepetitionInterval not set on trigger"
    }
    $repDuration = $readback.Triggers[0].Repetition.Duration
    if (-not $repDuration) {
        throw "Verification failed for ${TaskName}: RepetitionDuration not set on trigger"
    }

    $nextRun = (Get-ScheduledTaskInfo -TaskPath $taskPath -TaskName $TaskName).NextRunTime
    Write-Host ("Registered + verified: {0}{1} (S4U + Limited, daily {2}, every {3} min for {4} h {5} min, next run {6})" -f `
        $taskPath, $TaskName, $StartAt, $IntervalMinutes, $DurationHours, $DurationMinutes, $nextRun)
}

# Windows chosen so the two tasks never fire on the same minute:
#   Night: 22:00 through 07:58 (9 h 58 min, 2-min cadence, last tick 07:58)
#   Day:   08:00 through 21:58 (13 h 58 min, 10-min cadence, last tick 21:50)
# 2-minute boundary gap at 08:00 and 22:00 costs ~2 ticks/day (<0.6% coverage)
# well inside the 95% ISC floor; prevents JSONL append collisions.
Register-SamplerTask -TaskName "Jarvis-MemorySampler-Night" -StartAt "22:00" -IntervalMinutes 2  -DurationHours 9  -DurationMinutes 58
Register-SamplerTask -TaskName "Jarvis-MemorySampler-Day"   -StartAt "08:00" -IntervalMinutes 10 -DurationHours 13 -DurationMinutes 58
