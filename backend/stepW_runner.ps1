 $be = "D:\Projects\university-scheduler\backend"
 $env:PYTHONIOENCODING = "utf-8"
 $py = "$be\.venv\Scripts\python.exe"
 $ProgressPreference = 'SilentlyContinue'
if (-not (Test-Path $py)) { Write-Host "venv python missing" -ForegroundColor Red; return }
& $py -c "import sqlalchemy, pytest" 2>$null
if ($LASTEXITCODE -ne 0) { Write-Host "WRONG VENV (need sqlalchemy+pytest) - abort" -ForegroundColor Red; return }

Write-Host "=== T1: run pytest (phase2 suite) ===" -ForegroundColor Cyan
Push-Location $be
& $py -m pytest tests/test_phase2_services.py -o addopts="" -q --tb=short 2>&1
Pop-Location

Write-Host "`n=== T2: restart backend (picks up rotated key) ===" -ForegroundColor Cyan
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

Write-Host "`n=== T3: LLM live check with (new) key ===" -ForegroundColor Cyan
try {
  $st = Invoke-RestMethod "$base/api/ai/status" -TimeoutSec 10
  Write-Host ("  enabled=" + $st.llm.enabled + " | model=" + $st.llm.model)
  if ($st.llm.enabled) {
    $b = '{"question":"حداکثر واحد مجاز در مشروطی چیست؟","domain":"regulations"}'
    $r = Invoke-RestMethod -Method Post -Uri "$base/api/ai/ask" -ContentType "application/json; charset=utf-8" -Body $b -TimeoutSec 120
    Write-Host ("  engine=" + $r.engine + " | latency=" + $r.latency_ms + "ms")
    if ($r.engine -eq "llm") { Write-Host "  *** NEW KEY WORKS ***" -ForegroundColor Green }
    else { Write-Host "  engine != llm - check if old key was revoked in panel!" -ForegroundColor Red; Get-Content $out -Tail 8 }
  } else { Write-Host "  LLM disabled - key rotation skipped?" -ForegroundColor Yellow }
} catch { Write-Host ("  FAIL: " + $_.Exception.Message) -ForegroundColor Red }

Write-Host "`n=== T4: final sanity ===" -ForegroundColor Cyan
 $oa = Invoke-RestMethod "$base/openapi.json" -TimeoutSec 5
Write-Host ("  endpoints: " + @($oa.paths.PSObject.Properties.Name).Count)
(Invoke-RestMethod "$base/health") | ConvertTo-Json -Compress

Write-Host "`n=== BLOCK W DONE ===" -ForegroundColor Green
