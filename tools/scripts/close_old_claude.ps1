param([int]$AgeHours = 2, [switch]$Kill)

$cutoff = (Get-Date).AddHours(-$AgeHours)
$me = $PID

# Find candidate processes: claude.exe and node.exe (Claude Code runs on node)
$procs = Get-Process -ErrorAction SilentlyContinue | Where-Object {
    $_.ProcessName -match '^(claude|node)$' -and $_.Id -ne $me
}

$old = @()
foreach ($p in $procs) {
    try {
        $st = $p.StartTime
        if ($st -lt $cutoff) {
            # Try to get command line via CIM to filter for claude-code
            $ci = Get-CimInstance Win32_Process -Filter "ProcessId = $($p.Id)" -ErrorAction SilentlyContinue
            $cmd = $ci.CommandLine
            if ($p.ProcessName -eq 'claude' -or ($cmd -and $cmd -match 'claude')) {
                $old += [PSCustomObject]@{
                    Id        = $p.Id
                    Name      = $p.ProcessName
                    StartTime = $st
                    AgeHours  = [math]::Round(((Get-Date) - $st).TotalHours, 2)
                    Cmd       = if ($cmd) { $cmd.Substring(0, [Math]::Min(120, $cmd.Length)) } else { '' }
                }
            }
        }
    } catch {}
}

if (-not $old) {
    Write-Host "No claude processes older than $AgeHours hours found."
    exit 0
}

$old | Sort-Object StartTime | Format-Table -AutoSize -Wrap

if ($Kill) {
    Write-Host ""
    Write-Host "Killing $($old.Count) process(es)..."
    foreach ($o in $old) {
        try {
            Stop-Process -Id $o.Id -Force -ErrorAction Stop
            Write-Host "  killed PID $($o.Id) ($($o.Name))"
        } catch {
            Write-Host "  FAILED PID $($o.Id): $_"
        }
    }
} else {
    Write-Host ""
    Write-Host "Dry run. Re-run with -Kill to terminate."
}
