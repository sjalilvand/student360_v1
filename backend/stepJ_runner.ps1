 $be = "D:\Projects\university-scheduler\backend"
 $env:PYTHONIOENCODING = "utf-8"
 $py = "$be\.venv\Scripts\python.exe"
 $ProgressPreference = 'SilentlyContinue'

function Test-OurApp([int]$prt) {
  try { $oa = Invoke-RestMethod "http://127.0.0.1:$prt/openapi.json" -TimeoutSec 3; return ($oa.info.title -eq "Intelligent University Scheduler") } catch { return $false }
}
 $port = "8000"
if (Test-Path "$be\.runtime_port") { $port = (Get-Content "$be\.runtime_port" -Raw).Trim() }
 $base = "http://127.0.0.1:$port"

Write-Host "=== T1: server + demand/predict paths from OpenAPI ===" -ForegroundColor Cyan
 $dp = @()
try {
  $oa = Invoke-RestMethod "$base/openapi.json" -TimeoutSec 5
  Write-Host ("  server OK, endpoints: " + @($oa.paths.PSObject.Properties.Name).Count)
  $dp = @($oa.paths.PSObject.Properties.Name | Where-Object { $_ -match "demand|predict" })
  if ($dp) { $dp | ForEach-Object { Write-Host ("  path: " + $_) } }
  else { Write-Host "  NO demand/predict path registered" -ForegroundColor Yellow }
} catch { Write-Host "  server unreachable" -ForegroundColor Red }

Write-Host "`n=== T2: service diag (source + signatures + auto-invoke) ===" -ForegroundColor Cyan
Push-Location $be
& $py "_diag_demand.py"
Pop-Location

Write-Host "`n=== T3: refresh marts + sample v_course_demand ===" -ForegroundColor Cyan
try { (Invoke-RestMethod -Method Post -Uri "$base/api/marts/refresh" -TimeoutSec 30) | ConvertTo-Json -Compress } catch { Write-Host "  refresh failed" -ForegroundColor Red }
try { (Invoke-RestMethod "$base/api/marts/v_course_demand/sample?limit=5" -TimeoutSec 30) | ConvertTo-Json -Compress -Depth 4 } catch { Write-Host "  sample failed" -ForegroundColor Red }

Write-Host "`n=== T4: Vite ===" -ForegroundColor Cyan
try { $r = Invoke-WebRequest "http://127.0.0.1:5173" -TimeoutSec 3 -UseBasicParsing; Write-Host ("  Vite OK (" + $r.StatusCode + ")") -ForegroundColor Green }
catch { Write-Host "  Vite down" -ForegroundColor Yellow }

Write-Host "`n=== BLOCK J DONE ===" -ForegroundColor Green
