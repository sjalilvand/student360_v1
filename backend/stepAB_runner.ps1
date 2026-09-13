 $be = "D:\Projects\university-scheduler\backend"
 $env:PYTHONIOENCODING = "utf-8"
 $py = "$be\.venv\Scripts\python.exe"
 $ProgressPreference = 'SilentlyContinue'
if (-not (Test-Path $py)) { Write-Host "venv python missing" -ForegroundColor Red; return }
& $py -c "import sqlalchemy, pytest" 2>$null
if ($LASTEXITCODE -ne 0) { Write-Host "WRONG VENV - abort" -ForegroundColor Red; return }

Write-Host "=== T1: pytest (expect 16 passed) ===" -ForegroundColor Cyan
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
 $h = @{ "X-Student-Number" = "402101001" }

Write-Host "`n=== T3: recommend (the fixed 500 endpoint) ===" -ForegroundColor Cyan
 $tn = [uri]::EscapeDataString("متخصص هوش مصنوعی")
try {
  $r = Invoke-RestMethod "$base/api/career/recommend?track=$tn" -Headers $h -TimeoutSec 30
  Write-Host ("  track=" + $r.track + " | items=" + $r.items.Count)
  $r.items | ForEach-Object { Write-Host ("    " + $_.code + " | " + $_.title + " -> " + ($_.gives -join "، ")) }
} catch { Write-Host ("  STILL FAILING: " + $_.Exception.Message) -ForegroundColor Red; if ($_.ErrorDetails.Message) { Write-Host $_.ErrorDetails.Message } }

Write-Host "`n=== T4: career_readiness endpoint ===" -ForegroundColor Cyan
try {
  $rd = Invoke-RestMethod "$base/api/career/readiness" -Headers $h -TimeoutSec 20
  Write-Host ("  top=" + $rd.top_track.name + " (" + $rd.top_track.readiness_pct + "%) | skills=" + $rd.skills.Count)
} catch { Write-Host ("  FAIL: " + $_.Exception.Message) -ForegroundColor Red }

Write-Host "`n=== T5: sanity ===" -ForegroundColor Cyan
 $oa = Invoke-RestMethod "$base/openapi.json" -TimeoutSec 5
Write-Host ("  endpoints: " + @($oa.paths.PSObject.Properties.Name).Count)
(Invoke-RestMethod "$base/health") | ConvertTo-Json -Compress

Write-Host "`n=== BLOCK AB DONE ===" -ForegroundColor Green
