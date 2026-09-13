 $be = "D:\Projects\university-scheduler\backend"
 $env:PYTHONIOENCODING = "utf-8"
 $py = "$be\.venv\Scripts\python.exe"
 $ProgressPreference = 'SilentlyContinue'
if (-not (Test-Path $py)) { Write-Host "venv missing" -ForegroundColor Red; return }
& $py -c "import sqlalchemy, pytest, sklearn, joblib" 2>$null
if ($LASTEXITCODE -ne 0) { Write-Host "WRONG VENV" -ForegroundColor Red; return }

Write-Host "=== T1: pytest (expect 20 passed) ===" -ForegroundColor Cyan
Push-Location $be
& $py -m pytest tests/test_phase2_services.py -o addopts="" -q --tb=short 2>&1
Pop-Location

Write-Host "`n=== T2: restart backend ===" -ForegroundColor Cyan
function Test-OurApp([int]$prt) {
  try { $oa = Invoke-RestMethod "http://127.0.0.1:$prt/openapi.json" -TimeoutSec 3; return ($oa.info.title -eq "Intelligent University Scheduler") } catch { return $false }
}
 $port = "8000"
if (Test-Path "$be\.runtime_port") { $port = (Get-Content "$be\.runtime_port" -Raw).Trim() }
Get-NetTCPConnection -LocalPort ([int]$port) -State Listen -ErrorAction SilentlyContinue | ForEach-Object {
  $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue
  if ($p -and $p.ProcessName -match "python") { Stop-Process -Id $p.Id -Force; Write-Host "  stopped old PID $($p.Id)" }
}
Start-Sleep -Seconds 2
 $out = "$be\.runtime.out.log"; $err = "$be\.runtime.err.log"
Remove-Item $out, $err -ErrorAction SilentlyContinue
Start-Process -FilePath $py -ArgumentList @("-m","uvicorn","app.main:app","--host","127.0.0.1","--port","$port") -WorkingDirectory $be -WindowStyle Hidden -RedirectStandardOutput $out -RedirectStandardError $err
 $ready = $false
foreach ($i in 1..30) { Start-Sleep -Seconds 2; if (Test-OurApp ([int]$port)) { $ready = $true; break } }
if (-not $ready) { Write-Host "  NOT READY:" -ForegroundColor Red; Get-Content $err -Tail 30; return }
 $base = "http://127.0.0.1:$port"
Write-Host ("  READY: $base") -ForegroundColor Green
 $h = @{ "X-Student-Number" = "402101001" }

Write-Host "`n=== T3: train ML model (2 pilot students) ===" -ForegroundColor Cyan
try {
  (Invoke-RestMethod -Method Post -Uri "$base/api/risk-ml/train" -TimeoutSec 60) | ConvertTo-Json -Compress
} catch { Write-Host ("  FAIL: " + $_.Exception.Message) -ForegroundColor Red }

Write-Host "`n=== T4: predict for Ali ===" -ForegroundColor Cyan
try {
  (Invoke-RestMethod "$base/api/risk-ml/predict" -Headers $h -TimeoutSec 30) | ConvertTo-Json -Compress -Depth 3
} catch { Write-Host ("  FAIL: " + $_.Exception.Message) -ForegroundColor Red }

Write-Host "`n=== T5: PUSH ===" -ForegroundColor Cyan
Set-Location "D:\Projects\university-scheduler"
# ml_models (binaries) should not go to git
if (-not (Select-String -Path ".gitignore" -Pattern "ml_models" -Quiet)) {
  Add-Content -Path ".gitignore" -Value "", "backend/ml_models/" -Encoding UTF8
}
& ".\push_updates.ps1" "feat: ML risk scorer (RandomForest, distilled labels) + train/predict API"
Write-Host "`n=== BLOCK AQ DONE ===" -ForegroundColor Green
