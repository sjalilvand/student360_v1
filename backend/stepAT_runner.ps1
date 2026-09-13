 $be = "D:\Projects\university-scheduler\backend"
 $env:PYTHONIOENCODING = "utf-8"
 $py = "$be\.venv\Scripts\python.exe"
 $ProgressPreference = 'SilentlyContinue'
if (-not (Test-Path $py)) { Write-Host "venv missing" -ForegroundColor Red; return }
& $py -c "import sqlalchemy, pytest" 2>$null
if ($LASTEXITCODE -ne 0) { Write-Host "WRONG VENV" -ForegroundColor Red; return }

Write-Host "=== T1: pytest (expect 21 passed) ===" -ForegroundColor Cyan
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

Write-Host "`n=== T3: graph-aware RAG FINAL (1090 hint) ===" -ForegroundColor Cyan
try {
  $b = '{"question":"برای برداشتن مهندسی نرم‌افزار چه پیش‌نیازهایی لازم است؟","domain":"regulations"}'
  $r = Invoke-RestMethod -Method Post -Uri "$base/api/student360/regulations/ask" -Headers $h -Body $b -TimeoutSec 180
  $ans = if ($r.answer) { $r.answer } else { $r.response }
  Write-Host ("  engine=" + $r.ai_engine)
  Write-Host ("  answer[:550]: " + $ans.Substring(0, [Math]::Min(550, $ans.Length)))
} catch { Write-Host ("  FAIL: " + $_.Exception.Message) -ForegroundColor Red }

Write-Host "`n=== T4: PUSH ===" -ForegroundColor Cyan
Set-Location "D:\Projects\university-scheduler"
Get-ChildItem -Path . -Recurse -Include _fix_*.py,_diag_*.py,_retrain.py -File -ErrorAction SilentlyContinue |
  Where-Object { $_.FullName -notmatch '_trash_|node_modules|\.git\\' } |
  ForEach-Object { Remove-Item $_.FullName -Force }
& ".\push_updates.ps1" "fix: invisible-char normalization (LRM/ZWNJ/etc) + best-match course resolution in graph hint"
Write-Host "`n=== BLOCK AT DONE ===" -ForegroundColor Green
