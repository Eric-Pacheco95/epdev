Write-Host "=== Network throughput (3 sec sample) ===" -ForegroundColor Cyan
$samples = Get-Counter '\Network Interface(*)\Bytes Sent/sec','\Network Interface(*)\Bytes Received/sec' -SampleInterval 1 -MaxSamples 3
$samples.CounterSamples | Where-Object { $_.CookedValue -gt 5000 -and $_.InstanceName -notmatch 'isatap|loopback|teredo' } | Select-Object @{N='Direction';E={if($_.Path -match 'sent'){'UP'}else{'DN'}}}, InstanceName, @{N='KBps';E={[math]::Round($_.CookedValue/1024,1)}} | Format-Table -AutoSize

Write-Host "`n=== Fortnite connections ===" -ForegroundColor Cyan
Get-NetTCPConnection -State Established -OwningProcess 19320 -ErrorAction SilentlyContinue | Select-Object RemoteAddress, RemotePort | Format-Table -AutoSize

Write-Host "`n=== Top processes by current CPU% ===" -ForegroundColor Cyan
$p1 = Get-Process | Select-Object Id, Name, CPU
Start-Sleep -Seconds 2
$p2 = Get-Process | Select-Object Id, Name, CPU
$delta = foreach ($proc in $p2) {
  $prev = $p1 | Where-Object { $_.Id -eq $proc.Id }
  if ($prev) {
    [PSCustomObject]@{
      Name = $proc.Name
      Id = $proc.Id
      CPUDelta = [math]::Round(($proc.CPU - $prev.CPU), 2)
    }
  }
}
$delta | Sort-Object CPUDelta -Descending | Select-Object -First 10 | Format-Table -AutoSize
