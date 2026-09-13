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

Write-Host "`n=== T1: staff overview ===" -ForegroundColor Cyan
(Invoke-RestMethod "$base/api/staff/overview" -TimeoutSec 15) | ConvertTo-Json -Compress -Depth 4

Write-Host "`n=== T2: staff students ===" -ForegroundColor Cyan
(Invoke-RestMethod "$base/api/staff/students" -TimeoutSec 15) | ConvertTo-Json -Compress -Depth 4

Write-Host "`n=== T3: sanity ===" -ForegroundColor Cyan
 $oa = Invoke-RestMethod "$base/openapi.json" -TimeoutSec 5
Write-Host ("  endpoints: " + @($oa.paths.PSObject.Properties.Name).Count)

Write-Host "`n=== T4: Vite ===" -ForegroundColor Cyan
try { $r = Invoke-WebRequest "http://127.0.0.1:5173" -TimeoutSec 3 -UseBasicParsing; Write-Host ("  Vite OK (" + $r.StatusCode + ")") -ForegroundColor Green }
catch { Write-Host "  Vite down" -ForegroundColor Yellow }

Write-Host "`n=== BLOCK L DONE ===" -ForegroundColor Green
