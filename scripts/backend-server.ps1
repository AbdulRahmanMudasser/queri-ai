# scripts/backend-server.ps1
# PowerShell script to start the Queri.ai FastAPI backend server.

param (
    [string]$BindHost = "0.0.0.0",
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "           Queri.ai Backend Startup Assistant               " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 1. Resolve repository-relative paths
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
$BackendDir = Join-Path $RepoRoot "backend"
$EnvFile = Join-Path $BackendDir ".env"

Write-Host "[*] Resolving Path Structures..." -ForegroundColor Gray
Write-Host "    Project Root: $RepoRoot" -ForegroundColor Gray
Write-Host "    Backend Dir:  $BackendDir" -ForegroundColor Gray

if (-not (Test-Path $BackendDir)) {
    Write-Error "Prerequisite Missing: Backend Directory '$BackendDir' Not Found."
}

# 2. Check for Poetry
Write-Host "[*] Checking For Poetry Installation..." -ForegroundColor Gray
try {
    $poetryVersion = poetry --version
    Write-Host "[+] Poetry Detected: $poetryVersion" -ForegroundColor Green
}
catch {
    Write-Error "Poetry Is Not Installed Or Not Available In The Environment PATH. Please Install It First: https://python-poetry.org/docs/#installation"
}

# 3. Check for .env file
Write-Host "[*] Verifying .Env Configuration..." -ForegroundColor Gray
if (-not (Test-Path $EnvFile)) {
    Write-Error "Prerequisite Missing: Environment File '$EnvFile' Not Found. Please Create It First."
}
Write-Host "[+] Found Environment File." -ForegroundColor Green

# 4. Check if the port is already in use
Write-Host "[*] Checking Port $Port For Listening Processes..." -ForegroundColor Gray
$connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue

if ($connections) {
    $owningPid = $connections[0].OwningProcess
    $proc = Get-CimInstance Win32_Process -Filter "ProcessId = $owningPid" -ErrorAction SilentlyContinue
    if (-not $proc) {
        $proc = Get-Process -Id $owningPid -ErrorAction SilentlyContinue
    }
    
    if ($proc) {
        $processName = if ($proc.Name) { $proc.Name } else { $proc.ProcessName }
        $cmdLine = if ($proc.CommandLine) { $proc.CommandLine } else { "" }
        Write-Host "[!] Port $Port Is Currently Occupied By Process ID $owningPid ($processName)." -ForegroundColor Yellow
        
        # Check if the process is a running instance of our backend
        $isOurBackend = $false
        if ($cmdLine) {
            if ($cmdLine -like "*uvicorn*" -and ($cmdLine -like "*app.main:app*" -or $cmdLine -like "*queri-ai*")) {
                $isOurBackend = $true
            }
        }
        else {
            if ($processName -like "*uvicorn*" -or $processName -like "*python*") {
                $isOurBackend = $true
            }
        }
        
        if ($isOurBackend) {
            Write-Host "[+] The Backend Server Is Already Running On Port $Port." -ForegroundColor Green
            Write-Host "    Process: $processName (PID: $owningPid)" -ForegroundColor Green
            if ($cmdLine) {
                Write-Host "    Command: $cmdLine" -ForegroundColor Green
            }
            Exit 0
        }
        else {
            if ($cmdLine) {
                Write-Error "Port $Port Is Occupied By An Unrelated Process: '$processName' (PID: $owningPid). Command Line: $cmdLine. Please Free The Port First."
            } else {
                Write-Error "Port $Port Is Occupied By An Unrelated Process: '$processName' (PID: $owningPid). Please Free The Port First."
            }
        }
    }
    else {
        Write-Error "Port $Port Is Occupied By System/Unidentifiable Process ID $owningPid. Please Free The Port First."
    }
}
else {
    Write-Host "[+] Port $Port Is Free." -ForegroundColor Green
}

# 5. Verify / install dependencies
Write-Host "[*] Verifying Poetry Virtual Environment..." -ForegroundColor Gray
Push-Location $BackendDir
try {
    $envCheck = & poetry run python -c "import fastapi" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[*] Virtual Environment Or Dependencies Not Found. Running Dependency Installation..." -ForegroundColor Yellow
        poetry install
        Write-Host "[+] Dependencies Successfully Installed." -ForegroundColor Green
    }
    else {
        Write-Host "[+] Virtual Environment And Dependencies Verified." -ForegroundColor Green
    }
}
finally {
    Pop-Location
}

# 6. Start the server
Write-Host "[*] Spawning FastAPI Backend Server..." -ForegroundColor Cyan
Write-Host "[*] To Access The Application, Open: http://localhost:$Port Or http://127.0.0.1:$Port" -ForegroundColor Green
Push-Location $BackendDir
try {
    poetry run uvicorn app.main:app --host $BindHost --port $Port --reload
}
finally {
    Pop-Location
}
