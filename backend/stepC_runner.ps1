 $be = "D:\Projects\university-scheduler\backend"
 $fe = "D:\Projects\university-scheduler\frontend"
 $ProgressPreference = 'SilentlyContinue'
 $env:PYTHONIOENCODING = "utf-8"

function Test-OurApp([int]$prt) {
  try {
    $oa = Invoke-RestMethod "http://127.0.0.1:$prt/openapi.json" -TimeoutSec 3
    return ($oa.info.title -eq "Intelligent University Scheduler")
  } catch { return $false }
}

 $port = "8000"
if (Test-Path "$be\.runtime_port") { $port = (Get-Content "$be\.runtime_port" -Raw).Trim() }
if ((Get-NetTCPConnection -LocalPort ([int]$port) -State Listen -ErrorAction SilentlyContinue) -and -not (Test-OurApp ([int]$port))) {
  foreach ($cand in 8011..8020) {
    if (-not (Get-NetTCPConnection -LocalPort $cand -State Listen -ErrorAction SilentlyContinue)) { $port = "$cand"; break }
  }
  Write-Host "Port was foreign -> switched to $port"
}
Get-NetTCPConnection -LocalPort ([int]$port) -State Listen -ErrorAction SilentlyContinue | ForEach-Object {
  $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue
  if ($p -and $p.ProcessName -match "python") { Write-Host "Stopping old backend PID $($p.Id)"; Stop-Process -Id $p.Id -Force }
}
Start-Sleep -Seconds 2
 $py = "$be\.venv\Scripts\python.exe"
 $out = "$be\.runtime.out.log"; $err = "$be\.runtime.err.log"
Remove-Item $out, $err -ErrorAction SilentlyContinue
Start-Process -FilePath $py -ArgumentList @("-m","uvicorn","app.main:app","--host","127.0.0.1","--port","$port") -WorkingDirectory $be -WindowStyle Hidden -RedirectStandardOutput $out -RedirectStandardError $err
 $ready = $false
foreach ($i in 1..30) { Start-Sleep -Seconds 2; if (Test-OurApp ([int]$port)) { $ready = $true; break } }
if (-not $ready) { Write-Host "BACKEND NOT READY:" -ForegroundColor Red; Get-Content $err -Tail 40 -ErrorAction SilentlyContinue; return }
 $base = "http://127.0.0.1:$port"
Set-Content -LiteralPath "$be\.runtime_port" -Value "$port"
Write-Host "READY: $base" -ForegroundColor Green

Write-Host "`n=== T1: /api/ai/status (expect enabled:true) ===" -ForegroundColor Cyan
(Invoke-RestMethod "$base/api/ai/status") | ConvertTo-Json -Depth 5 -Compress

Write-Host "`n=== T2: refresh marts ===" -ForegroundColor Cyan
(Invoke-RestMethod -Method Post -Uri "$base/api/marts/refresh") | ConvertTo-Json -Compress

Write-Host "`n=== T3: marts status ===" -ForegroundColor Cyan
(Invoke-RestMethod "$base/api/marts/status") | ConvertTo-Json -Compress

Write-Host "`n=== T4: sample v_event_totals ===" -ForegroundColor Cyan
(Invoke-RestMethod "$base/api/marts/v_event_totals/sample?limit=10") | ConvertTo-Json -Compress -Depth 4

Write-Host "`n=== T5: audit logins (the old 404 path, expect 200) ===" -ForegroundColor Cyan
try { (Invoke-RestMethod "$base/api/v1/audit/logins?limit=5") | ConvertTo-Json -Compress -Depth 4 } catch { Write-Host "FAIL: $_" -ForegroundColor Red }

Write-Host "`n=== T6: REAL LLM ask (expect engine: llm) ===" -ForegroundColor Cyan
 $b1 = @{ question = "شرایط انتقال و مهمانی دانشجو چیست؟"; domain = "regulations"; student_ref = "402101001" } | ConvertTo-Json -Compress
try {
  $resp = Invoke-RestMethod -Method Post -Uri "$base/api/ai/ask" -ContentType "application/json; charset=utf-8" -Body $b1 -TimeoutSec 180
  Write-Host ("engine: " + $resp.engine + " | latency_ms: " + $resp.latency_ms + " | sources: " + $resp.sources.Count)
  Write-Host ("answer: " + $resp.answer.Substring(0, [Math]::Min(400, $resp.answer.Length)))
  if ($resp.engine -eq "llm") { Write-Host "*** SUCCESS: REAL LLM IS LIVE ***" -ForegroundColor Green }
  else {
    Write-Host "engine != llm -> stdout tail:" -ForegroundColor Red
    Get-Content $out -Tail 15 -ErrorAction SilentlyContinue
    Write-Host "`nProbing AvalAI model list..." -ForegroundColor Yellow
    $key = ((Get-Content "$be\.env") | Where-Object { $_ -like "OPENAI_API_KEY=*" }) -replace "^OPENAI_API_KEY=", ""
    try {
      $hdr = @{ Authorization = "Bearer $key" }
      $models = Invoke-RestMethod -Uri "https://api.avalai.ir/v1/models" -Headers $hdr -TimeoutSec 30
      Write-Host "Available gpt-5* models:" -ForegroundColor Yellow
      ($models.data.id | Where-Object { $_ -match "gpt-5" } | Select-Object -First 15) | ForEach-Object { Write-Host ("  " + $_) }
      Write-Host "HINT: pick one of the above, edit LLM_MODEL in backend\.env, then rerun this runner." -ForegroundColor Yellow
    } catch { Write-Host ("models probe failed: " + $_.Exception.Message) -ForegroundColor Red }
  }
} catch { Write-Host ("ask FAILED: " + $_.Exception.Message) -ForegroundColor Red; Get-Content $err -Tail 20 -ErrorAction SilentlyContinue }

Write-Host "`n=== T7: who calls /api/v1/audit/logins? ===" -ForegroundColor Cyan
 $hits = Get-ChildItem $fe\src -Recurse -Include *.jsx,*.js -File | Select-String -Pattern "audit/logins" -List
if ($hits) { $hits | ForEach-Object { Write-Host ("  caller: " + $_.Path) } }
else { Write-Host "  no caller found in frontend (was external/hot-reload stale code)" }

Write-Host "`n=== BLOCK C DONE ===" -ForegroundColor Green
