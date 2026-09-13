 $be = "D:\Projects\university-scheduler\backend"
 $fe = "D:\Projects\university-scheduler\frontend"
 $env:PYTHONIOENCODING = "utf-8"
 $py = "$be\.venv\Scripts\python.exe"
 $ProgressPreference = 'SilentlyContinue'
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
 $h = @{ "X-Student-Number" = "402101001" }

Write-Host "`n=== T0: JSX COMPILE CHECK via Vite (portal backtick fix!) ===" -ForegroundColor Cyan
foreach ($f in @("Student360Portal.jsx","StaffPages.jsx","BehaviorPage.jsx")) {
  try {
    $r = Invoke-WebRequest "http://127.0.0.1:5173/src/pages/student360/$f" -TimeoutSec 10 -UseBasicParsing
    Write-Host ("  $f -> " + $r.StatusCode + " (compiles OK)") -ForegroundColor Green
  } catch { Write-Host ("  $f -> COMPILE ERROR: " + $_.Exception.Message) -ForegroundColor Red }
}

Write-Host "`n=== T1: run scan (expect 2 created) ===" -ForegroundColor Cyan
(Invoke-RestMethod -Method Post -Uri "$base/api/intervention/run" -TimeoutSec 30) | ConvertTo-Json -Compress

Write-Host "`n=== T2: list ===" -ForegroundColor Cyan
 $list = Invoke-RestMethod "$base/api/intervention/list" -TimeoutSec 15
 $list.items | ForEach-Object { Write-Host ("  #" + $_.id + " | " + $_.student_number + " | " + $_.risk_score + " (" + $_.risk_level + ") | " + $_.status_label) }

Write-Host "`n=== T3: review first item (staff loop) ===" -ForegroundColor Cyan
 $fid = $list.items[0].id
 $rb = @{ status = "reviewed"; note = "با دانشجو تماس گرفته شد؛ برنامه حمایتی ترم آینده هماهنگ گردید."; reviewer = "staff-admin" } | ConvertTo-Json -Compress
(Invoke-RestMethod -Method Post -Uri "$base/api/intervention/$fid/review" -ContentType "application/json" -Body $rb -TimeoutSec 15) | ConvertTo-Json -Compress -Depth 4

Write-Host "`n=== T4: student view (transparency) ===" -ForegroundColor Cyan
(Invoke-RestMethod "$base/api/intervention/me" -Headers $h -TimeoutSec 15) | ConvertTo-Json -Compress -Depth 4

Write-Host "`n=== T5: re-scan idempotency (expect created=0, skipped=2) ===" -ForegroundColor Cyan
(Invoke-RestMethod -Method Post -Uri "$base/api/intervention/run" -TimeoutSec 30) | ConvertTo-Json -Compress

Write-Host "`n=== T6: sanity ===" -ForegroundColor Cyan
 $oa = Invoke-RestMethod "$base/openapi.json" -TimeoutSec 5
Write-Host ("  endpoints: " + @($oa.paths.PSObject.Properties.Name).Count)

Write-Host "`n=== BLOCK Q DONE ===" -ForegroundColor Green
