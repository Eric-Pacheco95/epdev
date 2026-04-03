$cutoff = (Get-Date).AddHours(-8)
$stale = Get-Process claude -ErrorAction SilentlyContinue | Where-Object { $_.StartTime -lt $cutoff }
if ($stale) {
    $count = $stale.Count
    $stale | ForEach-Object {
        $age = [math]::Round(((Get-Date) - $_.StartTime).TotalHours, 1)
        Write-Output "Killing PID $($_.Id) started $($_.StartTime) ($($age)h old)"
    }
    $stale | Stop-Process -Force -ErrorAction SilentlyContinue
    Write-Output "Killed $count stale claude session(s)."
} else {
    Write-Output "No stale sessions found (all under 8h old)."
}
