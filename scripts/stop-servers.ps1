[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = "Low")]
Param(
    [switch]$SkipBackend,
    [int[]]$BackendPorts = @(8000),
    [int]$GracefulWaitSeconds = 5
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
$backendDir = Join-Path $repoRoot "backend"

$backendNorm = [IO.Path]::GetFullPath($backendDir).ToLowerInvariant()

$summary = [ordered]@{
    backend = [ordered]@{ found = 0; stopped = 0; failed = 0 }
}

function Write-Step {
    param(
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)][string]$Message
    )
    Write-Host ("[{0}] {1}" -f $Label, $Message)
}

function Convert-CommandLineToComparableText {
    param([string]$CommandLine)
    if (-not $CommandLine) { return "" }
    return $CommandLine.Replace('/', '\').ToLowerInvariant()
}

function Test-IsProjectScopedCommand {
    param([string]$ComparableCommandLine)
    if (-not $ComparableCommandLine) { return $false }
    return $ComparableCommandLine.Contains($backendNorm)
}

function Convert-ToUnifiedProcess {
    param(
        [Parameter(Mandatory = $true)][object]$Process
    )
    $isCim = $Process.GetType().FullName -like "*CimInstance*"
    if ($isCim) {
        $processId = [int]$Process.ProcessId
        $name = "$($Process.Name)"
        $cmd = "$($Process.CommandLine)"
    } else {
        $processId = [int]$Process.Id
        $name = "$($Process.ProcessName)"
        $cmd = ""
    }
    
    return [PSCustomObject]@{
        ProcessId   = $processId
        Name        = $name
        CommandLine = $cmd
    }
}

function Get-ProcessesByCommandPattern {
    param(
        [Parameter(Mandatory = $true)][string[]]$Patterns,
        [switch]$RequireProjectScope
    )
    $procMatches = @()
    
    $all = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue
    if ($all) {
        foreach ($proc in $all) {
            $cmd = "$($proc.CommandLine)"
            if (-not $cmd) { continue }
            $cmp = Convert-CommandLineToComparableText -CommandLine $cmd
            if ($RequireProjectScope -and -not (Test-IsProjectScopedCommand -ComparableCommandLine $cmp)) {
                continue
            }
            foreach ($pattern in $Patterns) {
                if ($cmd -match $pattern) {
                    $procMatches += Convert-ToUnifiedProcess -Process $proc
                    break
                }
            }
        }
    }
    
    # Fallback to standard process lookup if WMI matches nothing or to supplement it
    $stdProcs = Get-Process -ErrorAction SilentlyContinue | Where-Object {
        $_.ProcessName -like "*uvicorn*"
    }
    foreach ($p in $stdProcs) {
        $targetProcessId = $p.Id
        $alreadyMatched = $false
        foreach ($m in $procMatches) {
            if ($m.ProcessId -eq $targetProcessId) {
                $alreadyMatched = $true
                break
            }
        }
        if (-not $alreadyMatched) {
            $procMatches += Convert-ToUnifiedProcess -Process $p
        }
    }

    return ($procMatches | Sort-Object ProcessId -Unique)
}

function Stop-ProcessGracefullyThenForce {
    param(
        [Parameter(Mandatory = $true)][int]$ProcessId,
        [int]$GracefulWait = 3
    )
    try {
        Stop-Process -Id $ProcessId -ErrorAction Stop
    } catch {
    }

    if ($GracefulWait -gt 0) {
        Start-Sleep -Seconds $GracefulWait
    }

    $alive = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if ($alive) {
        Stop-Process -Id $ProcessId -Force -ErrorAction Stop
    }
}

function Stop-ProcessTreeForce {
    param(
        [Parameter(Mandatory = $true)][int]$ProcessId
    )
    $taskkill = Get-Command taskkill.exe -ErrorAction SilentlyContinue
    if ($taskkill) {
        & $taskkill.Source /PID $ProcessId /T /F *> $null
        if ($LASTEXITCODE -eq 0) {
            return
        }
    }
    Stop-ProcessGracefullyThenForce -ProcessId $ProcessId -GracefulWait $GracefulWaitSeconds
}

function Stop-ProcessList {
    param(
        [Parameter(Mandatory = $true)][string]$Label,
        [AllowNull()][object[]]$Processes,
        [Parameter(Mandatory = $true)][System.Collections.IDictionary]$SectionSummary,
        [switch]$Compact,
        [switch]$TreeKill
    )
    if ($null -eq $Processes) { $Processes = @() }
    $SectionSummary.found = $Processes.Count
    if ($Processes.Count -eq 0) {
        Write-Step -Label $Label -Message "No Matching Processes Found."
        return
    }

    foreach ($p in $Processes) {
        $processId = $p.ProcessId
        $name = $p.Name
        $cmd = $p.CommandLine
        $target = "PID $processId ($name)"
        if ($PSCmdlet.ShouldProcess($target, "Stop Process")) {
            try {
                if ($TreeKill) {
                    Stop-ProcessTreeForce -ProcessId $processId
                } else {
                    Stop-ProcessGracefullyThenForce -ProcessId $processId -GracefulWait $GracefulWaitSeconds
                }
                $SectionSummary.stopped++
                if (-not $Compact) {
                    Write-Step -Label $Label -Message ("Stopped {0}" -f $target)
                    if ($cmd) { Write-Host ("  Cmd: {0}" -f $cmd) }
                }
            } catch {
                $SectionSummary.failed++
                if ($Compact) {
                    Write-Step -Label $Label -Message ("Failed To Stop {0}" -f $target)
                } else {
                    Write-Step -Label $Label -Message ("Failed To Stop {0}: {1}" -f $target, $_.Exception.Message)
                }
            }
        }
    }

    if ($Compact -and $Processes.Count -gt 0) {
        $names = @($Processes | ForEach-Object { $_.Name } | Sort-Object -Unique)
        $nameSummary = $names -join ", "
        Write-Step -Label $Label -Message ("Stopped {0} Process(es): {1}" -f $SectionSummary.stopped, $nameSummary)
    }
}

function Get-ProcessByPort {
    param(
        [Parameter(Mandatory = $true)][int]$Port
    )
    try {
        $conns = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
        if (-not $conns) { return @() }
        $pids = $conns | Select-Object -ExpandProperty OwningProcess -Unique
        $result = @()
        foreach ($p in $pids) {
            # 1. Check if the parent/creator process itself is alive
            $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$p" -ErrorAction SilentlyContinue
            if (-not $proc) {
                $proc = Get-Process -Id $p -ErrorAction SilentlyContinue
            }
            if ($proc) { 
                $result += Convert-ToUnifiedProcess -Process $proc 
            }

            # 2. Check if there are any child processes whose ParentProcessId is this PID
            $children = Get-CimInstance Win32_Process -Filter "ParentProcessId=$p" -ErrorAction SilentlyContinue
            if ($children) {
                foreach ($c in $children) { 
                    $result += Convert-ToUnifiedProcess -Process $c 
                }
            }

            # 3. Check for multiprocessing child command line mentions of parent_pid
            $allProcs = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue
            if ($allProcs) {
                foreach ($ap in $allProcs) {
                    if ($ap.CommandLine -like "*parent_pid=$p*") {
                        $result += Convert-ToUnifiedProcess -Process $ap
                    }
                }
            }
        }
        return ($result | Sort-Object ProcessId -Unique)
    } catch {
        return @()
    }
}

if (-not $SkipBackend) {
    $backendPatterns = @(
        'uvicorn.*app\.main:app'
    )
    $backendProcs = @(Get-ProcessesByCommandPattern -Patterns $backendPatterns -RequireProjectScope)
    if ($backendProcs.Count -eq 0) {
        Write-Step -Label "Backend" -Message "No Project-Scoped Backend Process Found. Retrying With Unscoped Detection."
        $backendProcs = @(Get-ProcessesByCommandPattern -Patterns $backendPatterns)
    }
    if ($backendProcs.Count -eq 0) {
        $fallbackBackendProcs = @()
        foreach ($port in $BackendPorts) {
            $fallbackBackendProcs += @(Get-ProcessByPort -Port $port)
        }
        $fallbackBackendProcs = @($fallbackBackendProcs | Sort-Object ProcessId -Unique)
        if ($fallbackBackendProcs.Count -gt 0) {
            Write-Step -Label "Backend" -Message ("Using Port-Based Detection On {0}." -f (($BackendPorts | ForEach-Object { ":$_" }) -join ", "))
            $backendProcs = $fallbackBackendProcs
        }
    }
    Stop-ProcessList -Label "Backend" -Processes $backendProcs -SectionSummary $summary.backend -TreeKill
}

Write-Host ""
Write-Host "Shutdown Summary:"
Write-Host ("  Backend: Found={0}, Stopped={1}, Failed={2}" -f $summary.backend.found, $summary.backend.stopped, $summary.backend.failed)
Write-Host ""
Write-Host "Shutdown Complete."
