 $be = "D:\Projects\university-scheduler\backend"
 $env:PYTHONIOENCODING = "utf-8"
 $py = "$be\.venv\Scripts\python.exe"
 $ProgressPreference = 'SilentlyContinue'
if (-not (Test-Path $py)) { Write-Host "venv python missing" -ForegroundColor Red; return }
& $py -c "import sqlalchemy, pytest" 2>$null
if ($LASTEXITCODE -ne 0) { Write-Host "WRONG VENV - abort" -ForegroundColor Red; return }

Write-Host "=== T1: pytest (expect 15 passed) ===" -ForegroundColor Cyan
Push-Location $be
& $py -m pytest tests/test_phase2_services.py -o addopts="" -q --tb=short 2>&1
Pop-Location

Write-Host "`n=== T2: backend sanity ===" -ForegroundColor Cyan
try {
  $oa = Invoke-RestMethod "http://127.0.0.1:8000/openapi.json" -TimeoutSec 5
  Write-Host ("  endpoints: " + @($oa.paths.PSObject.Properties.Name).Count)
  (Invoke-RestMethod "http://127.0.0.1:8000/health" -TimeoutSec 5) | ConvertTo-Json -Compress
} catch { Write-Host "  backend down" -ForegroundColor Yellow }

Write-Host "`n=== BLOCK Z DONE ===" -ForegroundColor Green
