 $be = "D:\Projects\university-scheduler\backend"
 $fe = "D:\Projects\university-scheduler\frontend"
 $env:PYTHONIOENCODING = "utf-8"
 $py = "$be\.venv\Scripts\python.exe"
 $ProgressPreference = 'SilentlyContinue'

if (-not (Test-Path $py)) { Write-Host "venv python missing" -ForegroundColor Red; return }
& $py -c "import sqlalchemy" 2>$null
if ($LASTEXITCODE -ne 0) { Write-Host "WRONG VENV (no sqlalchemy) - abort" -ForegroundColor Red; return }

function Test-OurApp([int]$prt) {
  try { $oa = Invoke-RestMethod "http://127.0.0.1:$prt/openapi.json" -TimeoutSec 3; return ($oa.info.title -eq "Intelligent University Scheduler") } catch { return $false }
}
 $port = "8000"
if (Test-Path "$be\.runtime_port") { $port = (Get-Content "$be\.runtime_port" -Raw).Trim() }
Get-NetTCPConnection -LocalPort ([int]$port) -State Listen -ErrorAction SilentlyContinue | ForEach-Object {
  $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue
  if ($p -and $p.ProcessName -match "python") { Stop-Process -Id $p.Id -Force; Write-Host "stopped old PID $($p.Id)" }
}
Start-Sleep -Seconds 2
 $out = "$be\.runtime.out.log"; $err = "$be\.runtime.err.log"
Remove-Item $out, $err -ErrorAction SilentlyContinue
Start-Process -FilePath $py -ArgumentList @("-m","uvicorn","app.main:app","--host","127.0.0.1","--port","$port") -WorkingDirectory $be -WindowStyle Hidden -RedirectStandardOutput $out -RedirectStandardError $err
 $ready = $false
foreach ($i in 1..30) { Start-Sleep -Seconds 2; if (Test-OurApp ([int]$port)) { $ready = $true; break } }
if (-not $ready) { Write-Host "NOT READY:" -ForegroundColor Red; Get-Content $err -Tail 30; return }
 $base = "http://127.0.0.1:$port"
Write-Host "READY: $base" -ForegroundColor Green

Write-Host "`n=== T0: curriculum schema (verify adaptive detection) ===" -ForegroundColor Cyan
Push-Location $be
& $py _diag_cur.py
Pop-Location

Write-Host "`n=== T1: studypath/me for Ali ===" -ForegroundColor Cyan
 $h = @{ "X-Student-Number" = "402101001" }
 $p = Invoke-RestMethod "$base/api/studypath/me" -Headers $h -TimeoutSec 20
Write-Host ("  program=" + $p.program + " | risk=" + $p.risk_level + " | max_units=" + $p.max_units_next_term.value)
Write-Host ("  summary: passed=" + $p.summary.passed_units + " inprog=" + $p.summary.in_progress_units + " remaining=" + $p.summary.remaining_units + " progress=" + $p.summary.progress_pct + "%")
Write-Host ("  cap reasons: " + ($p.max_units_next_term.reasons -join " | "))
Write-Host ("  plan terms: " + $p.plan.Count)
 $p.plan | ForEach-Object {
  Write-Host ("    [" + $_.label + "] " + $_.units + " units: " + (($_.courses | ForEach-Object { $_.title }) -join "، "))
}
if ($p.blocked.Count -gt 0) { Write-Host ("  blocked: " + (($p.blocked | ForEach-Object { $_.code }) -join "، ")) }

Write-Host "`n=== T2: staff view (Sara - no grades path) ===" -ForegroundColor Cyan
 $p2 = Invoke-RestMethod "$base/api/studypath/402101002" -TimeoutSec 20
Write-Host ("  max_units=" + $p2.max_units_next_term.value + " | risk=" + $p2.risk_level + " | terms=" + $p2.plan.Count)

Write-Host "`n=== T3: JSX compile check ===" -ForegroundColor Cyan
foreach ($f in @("Student360Portal.jsx","StudyPathPage.jsx")) {
  try { $r = Invoke-WebRequest "http://127.0.0.1:5173/src/pages/student360/$f" -TimeoutSec 10 -UseBasicParsing; Write-Host ("  $f -> OK") -ForegroundColor Green }
  catch { Write-Host ("  $f -> COMPILE ERROR") -ForegroundColor Red }
}

Write-Host "`n=== T4: sanity ===" -ForegroundColor Cyan
 $oa = Invoke-RestMethod "$base/openapi.json" -TimeoutSec 5
Write-Host ("  endpoints: " + @($oa.paths.PSObject.Properties.Name).Count)
try { $r = Invoke-WebRequest "http://127.0.0.1:5173" -TimeoutSec 3 -UseBasicParsing; Write-Host ("  Vite OK (" + $r.StatusCode + ")") -ForegroundColor Green } catch { Write-Host "  Vite down" -ForegroundColor Yellow }

Write-Host "`n=== BLOCK S DONE ===" -ForegroundColor Green
