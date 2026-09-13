 $be = "D:\Projects\university-scheduler\backend"
 $fe = "D:\Projects\university-scheduler\frontend"
 $ProgressPreference = 'SilentlyContinue'

function Test-OurApp([int]$prt) {
  try {
    $oa = Invoke-RestMethod "http://127.0.0.1:$prt/openapi.json" -TimeoutSec 3
    return ($oa.info.title -eq "Intelligent University Scheduler")
  } catch { return $false }
}

 $port = "8000"
if (Test-Path "$be\.runtime_port") { $port = (Get-Content "$be\.runtime_port" -Raw).Trim() }
Write-Host "Target port: $port"

if ((Get-NetTCPConnection -LocalPort ([int]$port) -State Listen -ErrorAction SilentlyContinue) -and -not (Test-OurApp ([int]$port))) {
  Write-Host "Port $port occupied by FOREIGN app - picking another port..."
  foreach ($cand in 8011..8020) {
    if (-not (Get-NetTCPConnection -LocalPort $cand -State Listen -ErrorAction SilentlyContinue)) { $port = "$cand"; break }
  }
  Write-Host "New port: $port"
}

 $conns = Get-NetTCPConnection -LocalPort ([int]$port) -State Listen -ErrorAction SilentlyContinue
foreach ($c in $conns) {
  $p = Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue
  if ($p -and $p.ProcessName -match "python") { Write-Host "Stopping old backend PID $($p.Id)"; Stop-Process -Id $p.Id -Force }
}
Start-Sleep -Seconds 2

 $py = "$be\.venv\Scripts\python.exe"; if (-not (Test-Path $py)) { $py = "python" }
 $out = "$be\.runtime.out.log"; $err = "$be\.runtime.err.log"
Remove-Item $out, $err -ErrorAction SilentlyContinue
Start-Process -FilePath $py -ArgumentList @("-m","uvicorn","app.main:app","--host","127.0.0.1","--port","$port") -WorkingDirectory $be -WindowStyle Hidden -RedirectStandardOutput $out -RedirectStandardError $err

 $ready = $false
foreach ($i in 1..30) { Start-Sleep -Seconds 2; if (Test-OurApp ([int]$port)) { $ready = $true; break } }
if (-not $ready) {
  Write-Host "BACKEND NOT READY - last logs:" -ForegroundColor Red
  Get-Content $err -Tail 40 -ErrorAction SilentlyContinue
  return
}
 $base = "http://127.0.0.1:$port"
Set-Content -LiteralPath "$be\.runtime_port" -Value "$port"
Write-Host "READY: $base" -ForegroundColor Green

 $oa = Invoke-RestMethod "$base/openapi.json"
 $paths = @($oa.paths.PSObject.Properties.Name)
Write-Host ("Total endpoints: " + $paths.Count)
Write-Host "--- new /api/ai paths ---"
 $paths | Where-Object { $_ -match "/api/ai" } | ForEach-Object { Write-Host ("  " + $_) }

Write-Host "`n=== T1: /api/ai/status ===" -ForegroundColor Cyan
(Invoke-RestMethod "$base/api/ai/status") | ConvertTo-Json -Depth 5 -Compress

Write-Host "`n=== T2: /api/ai/ask (regulations, Persian) ===" -ForegroundColor Cyan
 $b1 = @{ question = "شرط انتقال و ممنوع التحصیلی چیست"; domain = "regulations"; student_ref = "402101001" } | ConvertTo-Json -Compress
(Invoke-RestMethod -Method Post -Uri "$base/api/ai/ask" -ContentType "application/json; charset=utf-8" -Body $b1 -TimeoutSec 60) | ConvertTo-Json -Depth 5 -Compress

Write-Host "`n=== T3: /api/ai/ask (study, English) ===" -ForegroundColor Cyan
 $b2 = @{ question = "what are the graduation requirements"; domain = "study" } | ConvertTo-Json -Compress
(Invoke-RestMethod -Method Post -Uri "$base/api/ai/ask" -ContentType "application/json; charset=utf-8" -Body $b2 -TimeoutSec 60) | ConvertTo-Json -Depth 5 -Compress

Write-Host "`n=== T4: events summary (middleware proof) ===" -ForegroundColor Cyan
(Invoke-RestMethod "$base/api/events/summary?days=30") | ConvertTo-Json -Depth 5 -Compress

Write-Host "`n=== T5: recent http_request events (top 8) ===" -ForegroundColor Cyan
 $rec = Invoke-RestMethod "$base/api/events/recent?limit=200"
 $rec | Where-Object { $_.event_type -eq "http_request" } | Select-Object -First 8 | ForEach-Object {
  Write-Host ("  #" + $_.id + " | " + $_.event_name + " | " + $_.payload)
}

Write-Host "`n=== T6: LLM env hint ===" -ForegroundColor Cyan
if ($env:OPENAI_API_KEY) {
  Write-Host ("OPENAI_API_KEY is SET (len " + $env:OPENAI_API_KEY.Length + ") - real LLM enabled") -ForegroundColor Green
} else {
  Write-Host "OPENAI_API_KEY not set -> engine='retrieval' (RAG fallback). To enable later: set OPENAI_API_KEY (and optionally LLM_BASE_URL/LLM_MODEL), then rerun this runner." -ForegroundColor Yellow
}

Write-Host "`n=== T7: frontend files dump (for precise wiring next step) ===" -ForegroundColor Cyan
foreach ($f in @("src\main.jsx","src\pages\student360\LoginPage.jsx","src\pages\student360\Student360Portal.jsx","src\api\student360Api.js")) {
  Write-Host "`n----- $f -----" -ForegroundColor Yellow
  Get-Content (Join-Path $fe $f) -ErrorAction SilentlyContinue
}
Write-Host "`n=== STEP 2+3 DONE ===" -ForegroundColor Green
