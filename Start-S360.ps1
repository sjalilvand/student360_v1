# Start-S360.ps1 - راه‌انداز یکپارچه Student360 (بک‌اند + فرانت)
 $root = "D:\Projects\university-scheduler"
 $be = "$root\backend"; $fe = "$root\frontend"

function Test-OurApp([int]$prt) {
  try { $oa = Invoke-RestMethod "http://127.0.0.1:$prt/openapi.json" -TimeoutSec 3
        return ($oa.info.title -eq "Intelligent University Scheduler") } catch { return $false }
}

# --- backend (8000) ---
if (Test-OurApp 8000) { Write-Host "Backend: already running" -ForegroundColor DarkGreen }
else {
  $py = "$be\.venv\Scripts\python.exe"
  if (-not (Test-Path $py)) { Write-Host "venv missing!" -ForegroundColor Red; return }
  & $py -c "import sqlalchemy" 2>$null
  if ($LASTEXITCODE -ne 0) { Write-Host "WRONG VENV - abort" -ForegroundColor Red; return }
  $out = "$be\.runtime.out.log"; $err = "$be\.runtime.err.log"
  Start-Process -FilePath $py -ArgumentList @("-m","uvicorn","app.main:app","--host","127.0.0.1","--port","8000") -WorkingDirectory $be -WindowStyle Hidden -RedirectStandardOutput $out -RedirectStandardError $err
  Write-Host "Backend: starting on 8000 ..." -ForegroundColor Yellow
}

# --- frontend (5173) ---
 $viteOk = $false
try { $r = Invoke-WebRequest "http://127.0.0.1:5173" -TimeoutSec 2 -UseBasicParsing; if ($r.StatusCode -eq 200) { $viteOk = $true } } catch {}
if ($viteOk) { Write-Host "Frontend: already running" -ForegroundColor DarkGreen }
else {
  $npm = (Get-Command npm.cmd -ErrorAction SilentlyContinue).Source
  if (-not $npm) { $npm = (Get-Command npm -ErrorAction SilentlyContinue).Source }
  Start-Process -FilePath $npm -ArgumentList "run","dev" -WorkingDirectory $fe -WindowStyle Hidden -RedirectStandardOutput "$fe\.vite.out.log" -RedirectStandardError "$fe\.vite.err.log"
  Write-Host "Frontend: starting on 5173 ..." -ForegroundColor Yellow
}

# --- verify ---
 $okB = $false
foreach ($i in 1..30) { Start-Sleep -Seconds 2; if (Test-OurApp 8000) { $okB = $true; break } }
 $okF = $false
foreach ($i in 1..15) { Start-Sleep -Seconds 2; try { $r = Invoke-WebRequest "http://127.0.0.1:5173" -TimeoutSec 2 -UseBasicParsing; if ($r.StatusCode -eq 200) { $okF = $true; break } } catch {} }

Write-Host ""
if ($okB) { Write-Host "  BACKEND  OK : http://127.0.0.1:8000   (docs: /docs)" -ForegroundColor Green }
else { Write-Host "  BACKEND  FAIL -> log: backend\.runtime.err.log" -ForegroundColor Red }
if ($okF) { Write-Host "  FRONTEND OK : http://localhost:5173" -ForegroundColor Green }
else { Write-Host "  FRONTEND FAIL -> log: frontend\.vite.err.log" -ForegroundColor Red }
if ($okB -and $okF) { Start-Process "http://localhost:5173"; Write-Host "`n  Browser opened. موفق باشید!" -ForegroundColor Cyan }
