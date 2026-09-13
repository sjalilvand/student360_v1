 $be = "D:\Projects\university-scheduler\backend"
 $env:PYTHONIOENCODING = "utf-8"
 $py = "$be\.venv\Scripts\python.exe"
 $ProgressPreference = 'SilentlyContinue'
if (-not (Test-Path $py)) { Write-Host "venv python missing" -ForegroundColor Red; return }
& $py -c "import sqlalchemy, pytest" 2>$null
if ($LASTEXITCODE -ne 0) { Write-Host "WRONG VENV - abort" -ForegroundColor Red; return }

Write-Host "=== T1: pytest (expect 18 passed) ===" -ForegroundColor Cyan
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
 $h = @{ "X-Student-Number" = "402101001"; "Content-Type" = "application/json" }

Write-Host "`n=== T3: simulate then EXPLAIN ===" -ForegroundColor Cyan
try {
  $b = '{"courses":[{"title":"هوش مصنوعی","credits":3,"expected_grade":17},{"title":"شبکه","credits":3,"expected_grade":16},{"title":"کارآموزی","credits":3,"expected_grade":18},{"title":"پایگاه داده","credits":3,"expected_grade":15}]}'
  $sim = Invoke-RestMethod -Method Post -Uri "$base/api/twin/simulate" -Headers $h -Body $b -TimeoutSec 30
  Write-Host ("  sim ok: gpa " + $sim.before.gpa + " -> " + $sim.after.gpa + " | risk " + $sim.before.risk_score + " -> " + $sim.after.risk_score)

  $eb = @{ simulation = $sim } | ConvertTo-Json -Depth 6 -Compress
  $ex = Invoke-RestMethod -Method Post -Uri "$base/api/twin/explain" -Headers $h -Body $eb -TimeoutSec 120
  Write-Host ("  engine=" + $ex.engine)
  Write-Host ("  explanation: " + $ex.explanation)
} catch { Write-Host ("  FAIL: " + $_.Exception.Message) -ForegroundColor Red; if ($_.ErrorDetails.Message) { Write-Host $_.ErrorDetails.Message } }

Write-Host "`n=== T4: JSX compile ===" -ForegroundColor Cyan
foreach ($f in @("TwinPage.jsx")) {
  try { $r = Invoke-WebRequest "http://127.0.0.1:5173/src/pages/student360/$f" -TimeoutSec 10 -UseBasicParsing; Write-Host ("  $f -> OK") -ForegroundColor Green }
  catch { Write-Host ("  $f -> ERROR") -ForegroundColor Red; if ($_.ErrorDetails.Message) { $m=$_.ErrorDetails.Message; Write-Host ("    " + $m.Substring(0,[Math]::Min(400,$m.Length))) -ForegroundColor Yellow } }
}

Write-Host "`n=== T5: PUSH TO GITHUB ===" -ForegroundColor Cyan
Set-Location "D:\Projects\university-scheduler"
# cleanup bakfix files before push
Get-ChildItem -Path . -Recurse -Include *.bakfix,*.bakfix2 -File -ErrorAction SilentlyContinue |
  Where-Object { $_.FullName -notmatch '\\_trash_|node_modules|\.git\\' } |
  ForEach-Object { Remove-Item $_.FullName -Force; Write-Host ("  removed: " + $_.Name) }
git add -A
 $bad = git diff --cached --name-only | Where-Object { $_ -match "^\.env$|\.db$" }
if ($bad) { Write-Host ("  ABORT sensitive: " + ($bad -join ", ")) -ForegroundColor Red }
else {
  git commit -m "feat: Digital Twin LLM explainer (/api/twin/explain + UI button)" 2>&1 | Select-Object -Last 2
  git push origin main 2>&1 | ForEach-Object { Write-Host $_ }
  if ($LASTEXITCODE -eq 0) { Write-Host "  *** GITHUB UPDATED ***" -ForegroundColor Green }
}

Write-Host "`n=== BLOCK AI DONE ===" -ForegroundColor Green
