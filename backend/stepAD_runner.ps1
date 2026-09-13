 $be = "D:\Projects\university-scheduler\backend"
 $env:PYTHONIOENCODING = "utf-8"
 $py = "$be\.venv\Scripts\python.exe"
 $ProgressPreference = 'SilentlyContinue'
if (-not (Test-Path $py)) { Write-Host "venv python missing" -ForegroundColor Red; return }
& $py -c "import sqlalchemy, pytest" 2>$null
if ($LASTEXITCODE -ne 0) { Write-Host "WRONG VENV - abort" -ForegroundColor Red; return }

Write-Host "=== T1: pytest (expect 17 passed) ===" -ForegroundColor Cyan
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

Write-Host "`n=== T3: feedback quality stats ===" -ForegroundColor Cyan
 $q = Invoke-RestMethod "$base/api/feedback/quality?days=30" -TimeoutSec 20
Write-Host ("  conversations=" + $q.total_conversations + " | helpful=" + $q.helpful + " | not_helpful=" + $q.not_helpful + " | satisfaction=" + $q.satisfaction_pct + "% | low_conf=" + $q.low_confidence)

Write-Host "`n=== T4: LLM analyze (~10-30s) ===" -ForegroundColor Cyan
try {
  $ab = '{"days":30}'
  $a = Invoke-RestMethod -Method Post -Uri "$base/api/feedback/analyze" -ContentType "application/json" -Body $ab -TimeoutSec 180
  Write-Host ("  engine=" + $a.engine + " | themes=" + $a.insight.themes.Count)
  Write-Host ("  summary: " + $a.summary)
  $a.insight.recommendations | ForEach-Object { Write-Host ("    💡 " + $_) }
} catch { Write-Host ("  analyze FAILED: " + $_.Exception.Message) -ForegroundColor Red; if ($_.ErrorDetails.Message) { Write-Host $_.ErrorDetails.Message } }

Write-Host "`n=== T5: JSX compile ===" -ForegroundColor Cyan
foreach ($f in @("Student360Portal.jsx","StaffPages.jsx")) {
  try { $r = Invoke-WebRequest "http://127.0.0.1:5173/src/pages/student360/$f" -TimeoutSec 10 -UseBasicParsing; Write-Host ("  $f -> OK") -ForegroundColor Green }
  catch { Write-Host ("  $f -> COMPILE ERROR") -ForegroundColor Red }
}

Write-Host "`n=== T6: sanity ===" -ForegroundColor Cyan
 $oa = Invoke-RestMethod "$base/openapi.json" -TimeoutSec 5
Write-Host ("  endpoints: " + @($oa.paths.PSObject.Properties.Name).Count)
(Invoke-RestMethod "$base/health") | ConvertTo-Json -Compress

Write-Host "`n=== BLOCK AD DONE ===" -ForegroundColor Green
