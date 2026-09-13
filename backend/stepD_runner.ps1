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

Write-Host "`n=== T1: two rapid GETs with X-Student-Number (throttle + header test) ===" -ForegroundColor Cyan
try {
  $h = @{ "X-Student-Number" = "402101001" }
  Invoke-RestMethod "$base/api/student360/profile" -Headers $h -TimeoutSec 10 | Out-Null
  Invoke-RestMethod "$base/api/student360/profile" -Headers $h -TimeoutSec 10 | Out-Null
  Write-Host "  2 GETs done (1 should be logged, with student_ref=402101001)"
} catch { Write-Host ("  profile call: " + $_.Exception.Message) -ForegroundColor Yellow }

Write-Host "`n=== T2: recent http_request events ===" -ForegroundColor Cyan
 $rec = Invoke-RestMethod "$base/api/events/recent?limit=30"
 $rec | Where-Object { $_.event_type -eq "http_request" } | Select-Object -First 5 | ForEach-Object {
  Write-Host ("  #" + $_.id + " | " + $_.event_name + " | student_ref=" + $_.student_ref + " | " + $_.payload)
}

Write-Host "`n=== T3: summary ===" -ForegroundColor Cyan
(Invoke-RestMethod "$base/api/events/summary?days=7") | ConvertTo-Json -Compress -Depth 4
Write-Host "`n=== DONE ===" -ForegroundColor Green
