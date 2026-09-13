 $be = "D:\Projects\university-scheduler\backend"
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

Write-Host "`n=== T1: engagement (expect score>0) ===" -ForegroundColor Cyan
(Invoke-RestMethod "$base/api/behavior/engagement?days=30" -Headers $h -TimeoutSec 15) | ConvertTo-Json -Compress -Depth 4

Write-Host "`n=== T2: insights (expect peak_hour, trend, recommendations) ===" -ForegroundColor Cyan
 $ins = Invoke-RestMethod "$base/api/behavior/insights?days=30" -Headers $h -TimeoutSec 15
Write-Host ("  peak_hour=" + $ins.peak_hour + " | trend=" + $ins.trend + " | streak=" + $ins.streak_days + " | top=" + (($ins.top_features | Select-Object -First 3 | ForEach-Object { $_.type + ":" + $_.count }) -join ", "))
Write-Host "  recommendations:"
 $ins.recommendations | ForEach-Object { Write-Host ("    - " + $_) }

Write-Host "`n=== T3: staff ranking ===" -ForegroundColor Cyan
(Invoke-RestMethod "$base/api/behavior/ranking?days=30&limit=5" -TimeoutSec 15) | ConvertTo-Json -Compress -Depth 4

Write-Host "`n=== T4: sanity ===" -ForegroundColor Cyan
 $oa = Invoke-RestMethod "$base/openapi.json" -TimeoutSec 5
Write-Host ("  endpoints: " + @($oa.paths.PSObject.Properties.Name).Count)
try { $r = Invoke-WebRequest "http://127.0.0.1:5173" -TimeoutSec 3 -UseBasicParsing; Write-Host ("  Vite OK (" + $r.StatusCode + ")") -ForegroundColor Green } catch { Write-Host "  Vite down" -ForegroundColor Yellow }

Write-Host "`n=== BLOCK O DONE ===" -ForegroundColor Green
