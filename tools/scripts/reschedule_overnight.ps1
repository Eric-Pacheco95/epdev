# Overnight task reschedule — run elevated (Admin PowerShell)
# Generated 2026-04-17 per session_checkpoint.md

$log = "C:\Users\ericp\Github\epdev\tools\scripts\reschedule_overnight.log"
"Run: $(Get-Date)" | Out-File $log

$changes = @(
    @{ TN = "\Jarvis\Jarvis-SessionCleanup";           ST = "00:30" },
    @{ TN = "\Jarvis\Jarvis-IndexUpdate";              ST = "01:00" },
    @{ TN = "\Jarvis\JarvisEventRotation";             ST = "01:05" },
    @{ TN = "\Jarvis\Jarvis-HeartbeatRotation";        ST = "01:10" },
    @{ TN = "\Jarvis\Jarvis-SignalCompression";        ST = "01:15" },
    @{ TN = "\Jarvis\Jarvis-ParadigmHealth";           ST = "04:00" },
    @{ TN = "\Jarvis\Jarvis-Autoresearch-CodeQuality"; ST = "04:45" },
    @{ TN = "\Jarvis\Jarvis-TELOS-Introspection";      ST = "07:15" },
    @{ TN = "\Jarvis\Jarvis-Security-Audit";           ST = "08:00" }
)

foreach ($c in $changes) {
    try {
        $result = & schtasks /Change /TN $c.TN /ST $c.ST 2>&1
        if ($LASTEXITCODE -eq 0) {
            $tName = Split-Path $c.TN -Leaf
            $tPath = (Split-Path $c.TN -Parent) + "\"
            $task = Get-ScheduledTask -TaskName $tName -TaskPath $tPath -ErrorAction Stop
            $actual = ([datetime]$task.Triggers[0].StartBoundary).ToString("HH:mm")
            if ($actual -eq $c.ST) {
                $msg = "OK   $($c.TN): $actual"
            } else {
                $msg = "MISMATCH $($c.TN): expected $($c.ST) got $actual"
            }
        } else {
            $msg = "FAIL $($c.TN): $result"
        }
    } catch {
        $msg = "FAIL $($c.TN): $_"
    }
    Write-Host $msg
    $msg | Out-File $log -Append
}

Write-Host ""
Write-Host "--- Final schedule snapshot ---"
Get-ScheduledTask | Where-Object { $_.TaskName -like '*jarvis*' -or $_.TaskName -like '*Jarvis*' } | ForEach-Object {
    $task = Get-ScheduledTask -TaskName $_.TaskName -TaskPath $_.TaskPath
    $t = $task.Triggers[0]
    [PSCustomObject]@{
        Name  = $task.TaskName
        Start = if ($t.StartBoundary) { ([datetime]$t.StartBoundary).ToString("HH:mm") } else { $t.GetType().Name }
    }
} | Sort-Object Start | Format-Table -AutoSize | Tee-Object -FilePath $log -Append

Write-Host ""
Write-Host "Log saved to: $log"
Read-Host "Press Enter to close"
