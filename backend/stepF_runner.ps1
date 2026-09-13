 $be = "D:\Projects\university-scheduler\backend"
 $fe = "D:\Projects\university-scheduler\frontend"
 $ProgressPreference = 'SilentlyContinue'
 $env:PYTHONIOENCODING = "utf-8"
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
 $py = "$be\.venv\Scripts\python.exe"
 $out = "$be\.runtime.out.log"; $err = "$be\.runtime.err.log"
Remove-Item $out, $err -ErrorAction SilentlyContinue
Start-Process -FilePath $py -ArgumentList @("-m","uvicorn","app.main:app","--host","127.0.0.1","--port","$port") -WorkingDirectory $be -WindowStyle Hidden -RedirectStandardOutput $out -RedirectStandardError $err
 $ready = $false
foreach ($i in 1..30) { Start-Sleep -Seconds 2; if (Test-OurApp ([int]$port)) { $ready = $true; break } }
if (-not $ready) { Write-Host "NOT READY:" -ForegroundColor Red; Get-Content $err -Tail 30; return }
 $base = "http://127.0.0.1:$port"
Set-Content -LiteralPath "$be\.runtime_port" -Value "$port"
Write-Host "READY: $base" -ForegroundColor Green

Write-Host "`n=== T1: daily-jalali ===" -ForegroundColor Cyan
(Invoke-RestMethod "$base/api/events/daily-jalali?days=7") | ConvertTo-Json -Compress -Depth 4

Write-Host "`n=== T2: calendar-jalali (current month) ===" -ForegroundColor Cyan
 $cal = Invoke-RestMethod "$base/api/events/calendar-jalali"
Write-Host ("  month: " + $cal.month_name + " " + $cal.year + " | length: " + $cal.month_length + " | total: " + $cal.total_events + " | today: " + $cal.today_jalali)
 $withEvents = $cal.days | Where-Object { $_.count -gt 0 }
Write-Host ("  days with events: " + ($withEvents | ForEach-Object { "$($_.day)->$($_.count)" }) )

Write-Host "`n=== T3: gpa-mart (X-Student-Number header) ===" -ForegroundColor Cyan
 $h = @{ "X-Student-Number" = "402101001" }
(Invoke-RestMethod "$base/api/student360/profile/gpa-mart" -Headers $h) | ConvertTo-Json -Compress

Write-Host "`n=== T4: start Vite if down ===" -ForegroundColor Cyan
 $viteOk = $false
try { $r = Invoke-WebRequest "http://127.0.0.1:5173" -TimeoutSec 2 -UseBasicParsing; if ($r.StatusCode -eq 200) { $viteOk = $true } } catch {}
if ($viteOk) { Write-Host "  Vite already up" -ForegroundColor Green }
else {
  $npm = (Get-Command npm.cmd -ErrorAction SilentlyContinue).Source
  if (-not $npm) { $npm = (Get-Command npm -ErrorAction SilentlyContinue).Source }
  if (-not $npm) { Write-Host "  npm NOT FOUND" -ForegroundColor Red }
  else {
    $vout = "$fe\.vite.out.log"; $verr = "$fe\.vite.err.log"
    Remove-Item $vout, $verr -ErrorAction SilentlyContinue
    Start-Process -FilePath $npm -ArgumentList "run","dev" -WorkingDirectory $fe -WindowStyle Hidden -RedirectStandardOutput $vout -RedirectStandardError $verr
    foreach ($i in 1..15) { Start-Sleep -Seconds 2; try { $r = Invoke-WebRequest "http://127.0.0.1:5173" -TimeoutSec 2 -UseBasicParsing; if ($r.StatusCode -eq 200) { $viteOk = $true; break } } catch {} }
    if ($viteOk) { Write-Host "  VITE READY: http://localhost:5173" -ForegroundColor Green }
    else { Write-Host "  Vite failed - log:" -ForegroundColor Red; Get-Content $verr -Tail 15 -ErrorAction SilentlyContinue }
  }
}

Write-Host "`n=== T5: DUMP student360_profile.py (for precise GPA wiring next) ===" -ForegroundColor Cyan
Get-Content "$be\app\services\student360_profile.py"

Write-Host "`n=== T6: DUMP ProfilePage (from Student360Pages.jsx) ===" -ForegroundColor Cyan
 $src = Get-Content "$fe\src\pages\student360\Student360Pages.jsx" -Raw
 $start = $src.IndexOf("export function ProfilePage")
if ($start -lt 0) { $start = $src.IndexOf("function ProfilePage") }
 $next = $src.IndexOf("export function", $start + 10)
if ($start -ge 0 -and $next -gt $start) { Write-Host $src.Substring($start, $next - $start) }
else { Write-Host "ProfilePage bounds not found - will dump whole file head"; Write-Host $src.Substring(0, [Math]::Min(3000, $src.Length)) }

Write-Host "`n=== T7: demand prediction entry points ===" -ForegroundColor Cyan
(Select-String -Path "$be\app\services\demand_service.py" -Pattern '^def\s+(\w+)') | ForEach-Object { Write-Host ("  " + $_.Matches[0].Groups[1].Value + "()") }
(Select-String -Path "$be\app\api\routes_workflow.py" -Pattern '@\w+\.(get|post)\("([^"]*)"' | Where-Object { $_.Line -match "demand" }) | ForEach-Object { Write-Host ("  route: " + $_.Matches[0].Groups[1].Value + " " + $_.Matches[0].Groups[2].Value) }

Write-Host "`n=== BLOCK F DONE ===" -ForegroundColor Green
