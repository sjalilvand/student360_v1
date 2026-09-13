 $be = "D:\Projects\university-scheduler\backend"
 $env:PYTHONIOENCODING = "utf-8"
 $py = "$be\.venv\Scripts\python.exe"
 $ProgressPreference = 'SilentlyContinue'
if (-not (Test-Path $py)) { Write-Host "venv python missing" -ForegroundColor Red; return }
& $py -c "import sqlalchemy, pytest, networkx" 2>$null
if ($LASTEXITCODE -ne 0) { Write-Host "WRONG VENV (need networkx too) - abort" -ForegroundColor Red; return }

Write-Host "=== T1: pytest (expect 19 passed) ===" -ForegroundColor Cyan
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

Write-Host "`n=== T3: graph stats (real DB: 209 offered courses!) ===" -ForegroundColor Cyan
try { (Invoke-RestMethod "$base/api/graph/stats" -TimeoutSec 30) | ConvertTo-Json -Compress } catch { Write-Host ("  FAIL: " + $_.Exception.Message) -ForegroundColor Red; if ($_.ErrorDetails.Message) { Write-Host $_.ErrorDetails.Message } }

Write-Host "`n=== T4: roots (starter courses) ===" -ForegroundColor Cyan
try {
  $rt = Invoke-RestMethod "$base/api/graph/roots?limit=8" -TimeoutSec 30
  $rt.items | ForEach-Object { Write-Host ("    " + $_.code + " | " + $_.title + " | unlocks=" + $_.unlocks) }
} catch { Write-Host ("  FAIL: " + $_.Exception.Message) -ForegroundColor Red }

Write-Host "`n=== T5: course cluster (CS499 project) ===" -ForegroundColor Cyan
try {
  $cl = Invoke-RestMethod "$base/api/graph/course/CS499" -TimeoutSec 30
  Write-Host ("  " + $cl.title + " | direct_pre=" + ($cl.direct_prereqs -join ",") + " | recursive=" + ($cl.all_prereqs_recursive -join ",") + " | skills=" + ($cl.skills -join ","))
} catch { Write-Host ("  FAIL: " + $_.Exception.Message) -ForegroundColor Red }

Write-Host "`n=== T6: learning path (ریاضی عمومی 1 -> پایگاه داده?) ===" -ForegroundColor Cyan
try {
  $f = [uri]::EscapeDataString("ریاضی عمومی 1")
  $t = [uri]::EscapeDataString("پایگاه داده")
  $p = Invoke-RestMethod "$base/api/graph/path?from=$f&to=$t" -TimeoutSec 30
  if ($p.found) { $p.path | ForEach-Object { Write-Host ("    " + $_.i + ": " + $_.code + " " + $_.title) } }
  else { Write-Host ("  no path: " + $p.note) }
} catch { Write-Host ("  FAIL: " + $_.Exception.Message) -ForegroundColor Red }

Write-Host "`n=== T7: sanity ===" -ForegroundColor Cyan
 $oa = Invoke-RestMethod "$base/openapi.json" -TimeoutSec 5
Write-Host ("  endpoints: " + @($oa.paths.PSObject.Properties.Name).Count)
(Invoke-RestMethod "$base/health") | ConvertTo-Json -Compress

Write-Host "`n=== BLOCK AJ DONE ===" -ForegroundColor Green
