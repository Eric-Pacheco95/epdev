<#
.SYNOPSIS
    Enforce one-or-zero jarvis-app dev server instances.

.DESCRIPTION
    Manages the lifecycle of `next dev` processes in the jarvis-app repo so
    that at most one set runs at any time. Designed to be called from /vitals
    Phase 1.5 (-Ensure) and from a Task Scheduler reaper job (-Reap).

    SAFETY: This script ONLY targets node.exe processes whose CommandLine
    matches BOTH 'jarvis-app' AND ('next dev' OR 'npm.*run dev' OR
    'start-server.js' under jarvis-app). It will NEVER kill:
      - claude.exe (Claude Code harness)
      - generic node.exe procs (MCP servers, other tools)
      - python.exe / cmd.exe / pytest (hook spawns -- see handoff
        2026-04-28 evening: structural, not leaks)

.PARAMETER Status
    List current jarvis-app procs with age. No mutations.

.PARAMETER Stop
    Kill ALL jarvis-app procs unconditionally.

.PARAMETER Start
    Stop all, then start one fresh `npm run dev`.

.PARAMETER Ensure
    Idempotent: if exactly one healthy generation exists, do nothing.
    Otherwise: stop all, start one fresh.

.PARAMETER Reap
    Kill jarvis-app procs older than -MaxAgeHours (default 2). The youngest
    generation always survives. Designed for hourly scheduled task.

.PARAMETER MaxAgeHours
    Threshold for -Reap. Default 2.

.EXAMPLE
    .\jarvis_app_singleton.ps1 -Status
    .\jarvis_app_singleton.ps1 -Ensure       # Used by /vitals
    .\jarvis_app_singleton.ps1 -Reap         # Used by Task Scheduler
    .\jarvis_app_singleton.ps1 -Stop
#>
[CmdletBinding(DefaultParameterSetName='Status')]
param(
    [Parameter(ParameterSetName='Status')][switch]$Status,
    [Parameter(ParameterSetName='Stop')][switch]$Stop,
    [Parameter(ParameterSetName='Start')][switch]$Start,
    [Parameter(ParameterSetName='Ensure')][switch]$Ensure,
    [Parameter(ParameterSetName='Reap')][switch]$Reap,
    [int]$MaxAgeHours = 2,
    [string]$JarvisAppPath = 'C:\Users\ericp\Github\jarvis-app'
)

$ErrorActionPreference = 'Stop'

# ---------- Detection ----------
function Get-JarvisAppProcs {
    Get-CimInstance Win32_Process -Filter "Name = 'node.exe'" -ErrorAction SilentlyContinue |
        Where-Object {
            $cmd = $_.CommandLine
            if ([string]::IsNullOrEmpty($cmd)) { return $false }
            # Must mention jarvis-app
            if ($cmd -notmatch 'jarvis-app') { return $false }
            # Must be a dev-server proc (npm-cli run dev, next dev, or start-server.js under jarvis-app)
            return ($cmd -match 'next dev' -or `
                    $cmd -match 'npm.*run.*dev' -or `
                    $cmd -match 'jarvis-app.*start-server\.js' -or `
                    $cmd -match 'jarvis-app.*next.*dist.*bin')
        } |
        ForEach-Object {
            [PSCustomObject]@{
                ProcessId   = $_.ProcessId
                CreationDate = $_.CreationDate
                AgeHours    = [math]::Round(((Get-Date) - $_.CreationDate).TotalHours, 2)
                CommandLine = $_.CommandLine
            }
        } |
        Sort-Object CreationDate
}

# Group procs by 60-second windows; npm spawns 3 children per `run dev` in <5s,
# so a "generation" = procs with start times within 60s of each other.
function Group-Generations {
    param([object[]]$Procs)
    if (-not $Procs -or $Procs.Count -eq 0) { return @() }
    $generations = @()
    $current = @($Procs[0])
    for ($i = 1; $i -lt $Procs.Count; $i++) {
        $delta = ($Procs[$i].CreationDate - $current[-1].CreationDate).TotalSeconds
        if ($delta -lt 60) {
            $current += $Procs[$i]
        } else {
            $generations += , $current
            $current = @($Procs[$i])
        }
    }
    $generations += , $current
    return $generations
}

function Show-Status {
    $procs = Get-JarvisAppProcs
    if (-not $procs -or $procs.Count -eq 0) {
        Write-Output "[singleton] no jarvis-app dev procs running"
        return
    }
    $gens = Group-Generations -Procs $procs
    Write-Output "[singleton] $($procs.Count) procs across $($gens.Count) generation(s):"
    for ($g = 0; $g -lt $gens.Count; $g++) {
        $age = $gens[$g][0].AgeHours
        Write-Output "  gen $($g+1): $($gens[$g].Count) procs, age $age h, pids: $($gens[$g].ProcessId -join ', ')"
    }
}

function Stop-All {
    param([int[]]$ExceptPids = @())
    $procs = Get-JarvisAppProcs
    if (-not $procs -or $procs.Count -eq 0) {
        Write-Output "[singleton] nothing to stop"
        return 0
    }
    $killed = 0
    foreach ($p in $procs) {
        if ($ExceptPids -contains $p.ProcessId) { continue }
        try {
            Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop
            Write-Output "[singleton] killed pid=$($p.ProcessId) age=$($p.AgeHours)h"
            $killed++
        } catch {
            Write-Output "[singleton] miss pid=$($p.ProcessId) ($($_.Exception.Message))"
        }
    }
    return $killed
}

function Start-Fresh {
    if (-not (Test-Path $JarvisAppPath)) {
        Write-Error "[singleton] jarvis-app path not found: $JarvisAppPath"
        return
    }
    Write-Output "[singleton] starting fresh npm run dev in $JarvisAppPath"
    $logPath = Join-Path $JarvisAppPath '.singleton.log'
    Start-Process -FilePath 'cmd.exe' `
                  -ArgumentList '/c', "cd /d `"$JarvisAppPath`" && npm run dev > `"$logPath`" 2>&1" `
                  -WindowStyle Hidden
    Write-Output "[singleton] launched (log: $logPath)"
}

function Invoke-Reap {
    $procs = Get-JarvisAppProcs
    if (-not $procs -or $procs.Count -eq 0) {
        Write-Output "[singleton] reap: no procs"
        return
    }
    $gens = Group-Generations -Procs $procs
    if ($gens.Count -le 1 -and $gens[-1][0].AgeHours -lt $MaxAgeHours) {
        Write-Output "[singleton] reap: 1 healthy generation (age $($gens[-1][0].AgeHours)h), nothing to reap"
        return
    }
    # Always preserve the YOUNGEST generation; reap any other generation older than MaxAgeHours
    $youngestPids = $gens[-1] | ForEach-Object { $_.ProcessId }
    $reaped = 0
    foreach ($gen in $gens[0..($gens.Count - 2)]) {
        if ($gen[0].AgeHours -lt $MaxAgeHours) { continue }
        foreach ($p in $gen) {
            try {
                Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop
                Write-Output "[singleton] reaped pid=$($p.ProcessId) age=$($p.AgeHours)h"
                $reaped++
            } catch {
                Write-Output "[singleton] reap miss pid=$($p.ProcessId)"
            }
        }
    }
    Write-Output "[singleton] reap complete: killed $reaped, kept youngest generation ($($youngestPids.Count) procs)"
}

# ---------- Dispatch ----------
switch ($PSCmdlet.ParameterSetName) {
    'Status' { Show-Status }
    'Stop'   { [void](Stop-All) }
    'Start'  { [void](Stop-All); Start-Fresh }
    'Ensure' {
        $procs = Get-JarvisAppProcs
        $gens = Group-Generations -Procs $procs
        if ($gens.Count -eq 1 -and $gens[0][0].AgeHours -lt 24) {
            # Probe HTTP — if 200, healthy singleton; do nothing
            try {
                $resp = Invoke-WebRequest -Uri 'http://localhost:3000' -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
                if ($resp.StatusCode -eq 200) {
                    Write-Output "[singleton] ensure: healthy singleton at pid(s) $($gens[0].ProcessId -join ',') -- no action"
                    return
                }
            } catch {
                # fall through to restart
            }
        }
        Write-Output "[singleton] ensure: $($gens.Count) generation(s), restarting clean"
        [void](Stop-All)
        Start-Fresh
    }
    'Reap'   { Invoke-Reap }
    default  { Show-Status }
}
