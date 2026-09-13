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

Write-Host "`n=== T1: professor/ask WITH correct schema (expect llm + replaced) ===" -ForegroundColor Cyan
try {
  $b = @{ course_code = "CS201"; question = "پشته (stack) چیست و چه کاربردی دارد؟"; mode = "simple" } | ConvertTo-Json -Compress
  $r = Invoke-RestMethod -Method Post -Uri "$base/api/student360/professor/ask" -Headers $h -ContentType "application/json; charset=utf-8" -Body $b -TimeoutSec 180
  Write-Host ("  ai_engine=" + $r.ai_engine + " | ai_replaced=" + $r.ai_replaced + " | low_conf=" + $r.is_low_confidence + " | ai_sources=" + $r.ai_sources.Count)
  if ($r.answer) { Write-Host ("  answer[:300]: " + $r.answer.Substring(0, [Math]::Min(300, $r.answer.Length))) }
} catch { Write-Host ("  FAILED: " + $_.Exception.Message) -ForegroundColor Red; if ($_.ErrorDetails.Message) { Write-Host $_.ErrorDetails.Message } }

Write-Host "`n=== T2: regulations regression (expect llm again) ===" -ForegroundColor Cyan
try {
  $r2 = Invoke-RestMethod -Method Post -Uri "$base/api/student360/regulations/ask" -Headers $h -ContentType "application/json; charset=utf-8" -Body '{"question":"حداکثر واحد در وضعیت مشروطی چقدر است؟"}' -TimeoutSec 180
  Write-Host ("  ai_engine=" + $r2.ai_engine + " | ai_replaced=" + $r2.ai_replaced + " | is_low_confidence=" + $r2.is_low_confidence)
} catch { Write-Host ("  FAILED: " + $_.Exception.Message) -ForegroundColor Red }

Write-Host "`n=== T3: sanity ===" -ForegroundColor Cyan
 $oa = Invoke-RestMethod "$base/openapi.json" -TimeoutSec 5
Write-Host ("  endpoints: " + @($oa.paths.PSObject.Properties.Name).Count)

Write-Host "`n=== T4: Vite ===" -ForegroundColor Cyan
try { $r = Invoke-WebRequest "http://127.0.0.1:5173" -TimeoutSec 3 -UseBasicParsing; Write-Host ("  Vite OK (" + $r.StatusCode + ")") -ForegroundColor Green }
catch { Write-Host "  Vite down" -ForegroundColor Yellow }

Write-Host "`n=== BLOCK N DONE ===" -ForegroundColor Green
