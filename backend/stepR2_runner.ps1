 $be = "D:\Projects\university-scheduler\backend"
 $fe = "D:\Projects\university-scheduler\frontend"
 $env:PYTHONIOENCODING = "utf-8"
 $py = "$be\.venv\Scripts\python.exe"
 $ProgressPreference = 'SilentlyContinue'

# --- VENV GUARD (prevents wrong-project python) ---
if (-not (Test-Path $py)) { Write-Host "venv python missing" -ForegroundColor Red; return }
& $py -c "import sqlalchemy" 2>$null
if ($LASTEXITCODE -ne 0) { Write-Host "WRONG VENV (no sqlalchemy) - abort" -ForegroundColor Red; return }

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

Write-Host "`n=== T1: scan (expect created=0, skipped=2, cooldown_days=7) ===" -ForegroundColor Cyan
(Invoke-RestMethod -Method Post -Uri "$base/api/intervention/run" -TimeoutSec 30) | ConvertTo-Json -Compress

Write-Host "`n=== T2: final list ===" -ForegroundColor Cyan
 $list = Invoke-RestMethod "$base/api/intervention/list" -TimeoutSec 15
 $list.items | ForEach-Object { Write-Host ("  #" + $_.id + " | " + $_.student_number + " | " + $_.risk_level + " | " + $_.status_label + " | by:" + $_.reviewed_by) }

Write-Host "`n=== T3: student transparency ===" -ForegroundColor Cyan
 $h = @{ "X-Student-Number" = "402101001" }
(Invoke-RestMethod "$base/api/intervention/me" -Headers $h -TimeoutSec 15) | ConvertTo-Json -Compress -Depth 4

Write-Host "`n=== T4: sanity ===" -ForegroundColor Cyan
 $oa = Invoke-RestMethod "$base/openapi.json" -TimeoutSec 5
Write-Host ("  endpoints: " + @($oa.paths.PSObject.Properties.Name).Count)
try { $r = Invoke-WebRequest "http://127.0.0.1:5173" -TimeoutSec 3 -UseBasicParsing; Write-Host ("  Vite OK (" + $r.StatusCode + ")") -ForegroundColor Green } catch { Write-Host "  Vite down" -ForegroundColor Yellow }

Write-Host "`n=== BLOCK R2 DONE ===" -ForegroundColor Green
