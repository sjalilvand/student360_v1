 $be = "D:\Projects\university-scheduler\backend"
 $env:PYTHONIOENCODING = "utf-8"
 $py = "$be\.venv\Scripts\python.exe"
 $ProgressPreference = 'SilentlyContinue'
if (-not (Test-Path $py)) { Write-Host "venv python missing" -ForegroundColor Red; return }
& $py -c "import sqlalchemy" 2>$null
if ($LASTEXITCODE -ne 0) { Write-Host "WRONG VENV - abort" -ForegroundColor Red; return }

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

Write-Host "`n=== T0: what does offered_courses.prerequisite look like? ===" -ForegroundColor Cyan
Push-Location $be
& $py -c "import sqlite3,sys; sys.stdout.reconfigure(encoding='utf-8'); con=sqlite3.connect('university_scheduler.db'); [print(' ', r[0], '-> pre:', repr(r[1])) for r in con.execute('SELECT unique_code, prerequisite FROM offered_courses WHERE prerequisite IS NOT NULL AND prerequisite != ' + chr(39)+chr(39) + ' LIMIT 6')]; con.close()"
Pop-Location

Write-Host "`n=== T1: studypath Ali (with prereqs) ===" -ForegroundColor Cyan
 $h = @{ "X-Student-Number" = "402101001" }
 $p = Invoke-RestMethod "$base/api/studypath/me" -Headers $h -TimeoutSec 20
Write-Host ("  max_units=" + $p.max_units_next_term.value + " | plan terms=" + $p.plan.Count + " | blocked=" + $p.blocked.Count)
 $p.plan | ForEach-Object {
  Write-Host ("    [" + $_.label + "] " + $_.units + "u: " + (($_.courses | ForEach-Object { $_.code + "-" + $_.title }) -join " | "))
}
if ($p.blocked.Count -gt 0) {
  Write-Host "  BLOCKED (missing prereqs):"
  $p.blocked | ForEach-Object { Write-Host ("    " + $_.code + " " + $_.title + " <- needs: " + ($_.missing_prereqs -join ",")) }
}

Write-Host "`n=== T2: sanity ===" -ForegroundColor Cyan
 $oa = Invoke-RestMethod "$base/openapi.json" -TimeoutSec 5
Write-Host ("  endpoints: " + @($oa.paths.PSObject.Properties.Name).Count)
try { $r = Invoke-WebRequest "http://127.0.0.1:5173" -TimeoutSec 3 -UseBasicParsing; Write-Host ("  Vite OK (" + $r.StatusCode + ")") -ForegroundColor Green } catch { Write-Host "  Vite down" -ForegroundColor Yellow }

Write-Host "`n=== BLOCK T DONE ===" -ForegroundColor Green
