$ErrorActionPreference = "Stop"

$ProjectPath = "D:\Projects\university-scheduler"
$BackendPath = Join-Path $ProjectPath "backend"
$FrontendPath = Join-Path $ProjectPath "frontend"
$PythonExe = Join-Path $BackendPath ".venv\Scripts\python.exe"

function Test-PortInUse {
    param([int]$Port)
    return $null -ne (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host " University Scheduler - Starting Services" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

if (-not (Test-Path $PythonExe)) {
    Write-Host "Backend Python environment was not found." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Host "Node.js / npm was not found." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

if (Test-PortInUse -Port 8000) {
    Write-Host "Backend is already running on port 8000." -ForegroundColor Yellow
}
else {
    Write-Host "Starting Backend: http://127.0.0.1:8000" -ForegroundColor Yellow

    Start-Process powershell.exe -ArgumentList @(
        "-NoExit",
        "-ExecutionPolicy", "Bypass",
        "-Command",
        "Set-Location '$BackendPath'; & '$PythonExe' -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
    )
}

if (Test-PortInUse -Port 5173) {
    Write-Host "Frontend is already running on port 5173." -ForegroundColor Yellow
}
else {
    Write-Host "Starting Frontend: http://localhost:5173" -ForegroundColor Yellow

    Start-Process powershell.exe -ArgumentList @(
        "-NoExit",
        "-ExecutionPolicy", "Bypass",
        "-Command",
        "Set-Location '$FrontendPath'; npm run dev -- --host 127.0.0.1 --port 5173 --strictPort"
    )
}

Write-Host "Waiting for Backend..." -ForegroundColor Yellow

$BackendReady = $false
for ($i = 1; $i -le 30; $i++) {
    try {
        $Response = Invoke-WebRequest "http://127.0.0.1:8000/health" -UseBasicParsing -TimeoutSec 2
        if ($Response.StatusCode -eq 200) {
            $BackendReady = $true
            break
        }
    }
    catch {
        Start-Sleep -Seconds 1
    }
}

if ($BackendReady) {
    Write-Host "Backend is ready: http://127.0.0.1:8000/docs" -ForegroundColor Green
}
else {
    Write-Host "Backend did not respond yet. Check its separate window for errors." -ForegroundColor Yellow
}

Start-Sleep -Seconds 2
Start-Process "http://localhost:5173"

Write-Host ""
Write-Host "Frontend: http://localhost:5173" -ForegroundColor Green
Write-Host "Backend docs: http://127.0.0.1:8000/docs" -ForegroundColor Green