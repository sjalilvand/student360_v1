 $be = "D:\Projects\university-scheduler\backend"
 $env:PYTHONIOENCODING = "utf-8"
 $py = "$be\.venv\Scripts\python.exe"
 $ProgressPreference = 'SilentlyContinue'
if (-not (Test-Path $py)) { Write-Host "venv missing" -ForegroundColor Red; return }
& $py -c "import sqlalchemy, pytest" 2>$null
if ($LASTEXITCODE -ne 0) { Write-Host "WRONG VENV" -ForegroundColor Red; return }

Write-Host "=== T0: check if GAM2/GAM3 patches were applied ===" -ForegroundColor Cyan
 $enhOk = Select-String -Path "$be\app\services\ai_enhancer.py" -Pattern "_graph_hint" -Quiet
 $twinOk = Select-String -Path "$be\app\services\digital_twin_service.py" -Pattern "graph fallback" -Quiet
Write-Host ("  ai_enhancer graph-hint: " + $enhOk)
Write-Host ("  twin graph-fallback: " + $twinOk)

Write-Host "`n=== T1: pytest ===" -ForegroundColor Cyan
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

Write-Host "`n=== T3: graph-aware RAG ask ===" -ForegroundColor Cyan
try {
  $b = '{"question":"برای برداشتن مهندسی نرم‌افزار چه پیش‌نیازهایی لازم است؟","domain":"regulations"}'
  $r = Invoke-RestMethod -Method Post -Uri "$base/api/student360/regulations/ask" -Headers $h -Body $b -TimeoutSec 180
  Write-Host ("  ai_engine=" + $r.ai_engine)
  $ans = if ($r.answer) { $r.answer } else { $r.response }
  if ($ans) { Write-Host ("  answer[:450]: " + $ans.Substring(0, [Math]::Min(450, $ans.Length))) }
} catch { Write-Host ("  FAIL: " + $_.Exception.Message) -ForegroundColor Red }

Write-Host "`n=== T4: twin graph-fallback test ===" -ForegroundColor Cyan
try {
  $b2 = '{"courses":[{"title":"پروژه","credits":3,"expected_grade":17},{"title":"مدار منطقی","credits":3,"expected_grade":15}]}'
  $r2 = Invoke-RestMethod -Method Post -Uri "$base/api/twin/simulate" -Headers $h -Body $b2 -TimeoutSec 30
  Write-Host ("  skill_preview: " + ($r2.skill_preview | ConvertTo-Json -Compress))
} catch { Write-Host ("  FAIL: " + $_.Exception.Message) -ForegroundColor Red }

Write-Host "`n=== T5: PUSH (smart gate) ===" -ForegroundColor Cyan
Set-Location "D:\Projects\university-scheduler"
git add -A
 $bad = git diff --cached --name-only --diff-filter=ACMR | Where-Object { $_ -match "^\.env$|\.db$|node_modules/" }
if ($bad) { Write-Host ("  ABORT: " + ($bad -join ", ")) -ForegroundColor Red }
else {
  git commit -m "feat: graph-aware RAG answers + twin graph skill fallback" 2>&1 | Select-Object -Last 2
  git push origin main 2>&1 | Select-Object -Last 2
  if ($LASTEXITCODE -eq 0) { Write-Host "  *** GITHUB UPDATED ***" -ForegroundColor Green }
}

Write-Host "`n=== GAM 2+3 DONE ===" -ForegroundColor Green
