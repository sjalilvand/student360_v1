 $be = "D:\Projects\university-scheduler\backend"
 $env:PYTHONIOENCODING = "utf-8"
 $py = "$be\.venv\Scripts\python.exe"
 $ProgressPreference = 'SilentlyContinue'
if (-not (Test-Path $py)) { Write-Host "venv python missing" -ForegroundColor Red; return }
& $py -c "import sqlalchemy, pytest, networkx" 2>$null
if ($LASTEXITCODE -ne 0) { Write-Host "WRONG VENV - abort" -ForegroundColor Red; return }

Write-Host "=== T1: pytest (expect 19 passed) ===" -ForegroundColor Cyan
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

Write-Host "`n=== T3: stats AFTER cleanup (nan must be gone) ===" -ForegroundColor Cyan
try {
  $st = Invoke-RestMethod "$base/api/graph/stats" -TimeoutSec 30
  Write-Host ("  courses=" + $st.courses + " | prereq_edges=" + $st.prereq_edges + " | roots=" + $st.roots_count)
  $nanInRoots = $st.roots | Where-Object { $_ -eq "nan" }
  if ($nanInRoots) { Write-Host "  nan STILL in roots!" -ForegroundColor Red }
  else { Write-Host "  nan filtered ✔" -ForegroundColor Green }
} catch { Write-Host ("  FAIL: " + $_.Exception.Message) -ForegroundColor Red }

Write-Host "`n=== T4: roots top (real courses now) ===" -ForegroundColor Cyan
try {
  $rt = Invoke-RestMethod "$base/api/graph/roots?limit=6" -TimeoutSec 30
  $rt.items | ForEach-Object { Write-Host ("    " + $_.code + " | " + $_.title + " | unlocks=" + $_.unlocks) }
} catch { Write-Host ("  FAIL: " + $_.Exception.Message) -ForegroundColor Red }

Write-Host "`n=== T5: fuzzy cluster (CS499 / عنوان) ===" -ForegroundColor Cyan
foreach ($q in @("CS499","1044","پروژه")) {
  try {
    $cl = Invoke-RestMethod ("$base/api/graph/course/" + [uri]::EscapeDataString($q)) -TimeoutSec 30
    if ($cl.error) { Write-Host ("  $q -> " + $cl.error) -ForegroundColor Yellow }
    else { Write-Host ("  $q -> " + $cl.code + " | " + $cl.title + " | unlocks=" + $cl.unlocks_count + " | cond=" + $cl.conditions.Count) }
  } catch { Write-Host ("  $q FAIL") -ForegroundColor Red }
}

Write-Host "`n=== T6: fuzzy path ===" -ForegroundColor Cyan
try {
  $f = [uri]::EscapeDataString("ریاضی عمومی 1"); $t = [uri]::EscapeDataString("پایگاه داده")
  $p = Invoke-RestMethod "$base/api/graph/path?from=$f&to=$t" -TimeoutSec 30
  if ($p.found) { Write-Host ("  FOUND len=" + $p.length); $p.path | ForEach-Object { Write-Host ("    " + $_.i + ": " + $_.title) } }
  else { Write-Host ("  no path (" + ($p.note ?? $p.error) + ")") }
} catch { Write-Host ("  FAIL: " + $_.Exception.Message) -ForegroundColor Red }

Write-Host "`n=== T7: JSX compile ===" -ForegroundColor Cyan
foreach ($f in @("StaffPages.jsx","Student360Portal.jsx")) {
  try { $r = Invoke-WebRequest "http://127.0.0.1:5173/src/pages/student360/$f" -TimeoutSec 10 -UseBasicParsing; Write-Host ("  $f -> OK") -ForegroundColor Green }
  catch { Write-Host ("  $f -> ERROR") -ForegroundColor Red; if ($_.ErrorDetails.Message) { $m=$_.ErrorDetails.Message; Write-Host ("    " + $m.Substring(0,[Math]::Min(400,$m.Length))) -ForegroundColor Yellow } }
}

Write-Host "`n=== T8: PUSH TO GITHUB ===" -ForegroundColor Cyan
Set-Location "D:\Projects\university-scheduler"
& ".\push_updates.ps1" "feat: Knowledge Graph (courses/prereqs/skills) + staff Graph Explorer + data-quality fixes"
Write-Host "`n=== BLOCK AK DONE ===" -ForegroundColor Green
