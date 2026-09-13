 $be = "D:\Projects\university-scheduler\backend"
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

Write-Host "`n=== T1: refresh marts (expect 5 created, 0 skipped) ===" -ForegroundColor Cyan
(Invoke-RestMethod -Method Post -Uri "$base/api/marts/refresh") | ConvertTo-Json -Compress

Write-Host "`n=== T2: marts status ===" -ForegroundColor Cyan
(Invoke-RestMethod "$base/api/marts/status") | ConvertTo-Json -Compress

Write-Host "`n=== T3: v_student_gpa sample ===" -ForegroundColor Cyan
(Invoke-RestMethod "$base/api/marts/v_student_gpa/sample?limit=10") | ConvertTo-Json -Compress -Depth 4

Write-Host "`n=== T4: v_course_demand sample (top rows) ===" -ForegroundColor Cyan
 $d = (Invoke-RestMethod "$base/api/marts/v_course_demand/sample?limit=5")
 $d | ConvertTo-Json -Compress -Depth 4

Write-Host "`n=== T5: v_term_enrollment sample ===" -ForegroundColor Cyan
(Invoke-RestMethod "$base/api/marts/v_term_enrollment/sample?limit=10") | ConvertTo-Json -Compress -Depth 4

Write-Host "`n=== T6: Vite check ===" -ForegroundColor Cyan
try { $r = Invoke-WebRequest "http://127.0.0.1:5173" -TimeoutSec 3 -UseBasicParsing; Write-Host ("Vite OK (" + $r.StatusCode + ")") -ForegroundColor Green }
catch { Write-Host "Vite not running - start it: cd frontend; npm run dev" -ForegroundColor Yellow }

Write-Host "`n=== BLOCK E DONE ===" -ForegroundColor Green
Write-Host "BROWSER: http://localhost:5173 -> admin mode -> button [📊 داشبورد تحلیل] (bottom-left)" -ForegroundColor Magenta
