 $be = "D:\Projects\university-scheduler\backend"
 $ProgressPreference = 'SilentlyContinue'

# --- .env with AvalAI config (uses AVALAI_API_KEY env var if already set, else prompts once) ---
 $key = $env:AVALAI_API_KEY
if ($key) { Write-Host "Using AVALAI_API_KEY from environment (len $($key.Length))" -ForegroundColor Cyan }
else { $key = Read-Host "Paste your AvalAI API key" }

if ([string]::IsNullOrWhiteSpace($key)) {
  Write-Host "NO KEY -> staying in retrieval mode" -ForegroundColor Yellow
} else {
  $envText = "LLM_PROVIDER=openai`nOPENAI_API_KEY=$key`nLLM_BASE_URL=https://api.avalai.ir/v1`nLLM_MODEL=gpt-5.4`nLLM_TEMPERATURE=0.2`nLLM_MAX_TOKENS=800"
  Set-Content -LiteralPath "$be\.env" -Value $envText -Encoding ASCII
  Write-Host ".env written (AvalAI, model gpt-5.4)" -ForegroundColor Green
}

# --- ensure .gitignore covers .env ---
 $gi = "D:\Projects\university-scheduler\.gitignore"
if ((Test-Path $gi) -and -not (Select-String -LiteralPath $gi -Pattern '(?m)^\.env\s*$' -Quiet)) {
  Add-Content -LiteralPath $gi -Value ".env" -Encoding UTF8
  Write-Host "added .env to .gitignore"
}

# --- restart backend ---
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
 $py = "$be\.venv\Scripts\python.exe"; if (-not (Test-Path $py)) { $py = "python" }
 $out = "$be\.runtime.out.log"; $err = "$be\.runtime.err.log"
Remove-Item $out, $err -ErrorAction SilentlyContinue
Start-Process -FilePath $py -ArgumentList @("-m","uvicorn","app.main:app","--host","127.0.0.1","--port","$port") -WorkingDirectory $be -WindowStyle Hidden -RedirectStandardOutput $out -RedirectStandardError $err
 $ready = $false
foreach ($i in 1..30) { Start-Sleep -Seconds 2; if (Test-OurApp ([int]$port)) { $ready = $true; break } }
if (-not $ready) { Write-Host "BACKEND NOT READY:" -ForegroundColor Red; Get-Content $err -Tail 30 -ErrorAction SilentlyContinue; return }
 $base = "http://127.0.0.1:$port"
Set-Content -LiteralPath "$be\.runtime_port" -Value "$port"
Write-Host "READY: $base" -ForegroundColor Green

# --- T1: status (expect enabled: true) ---
Write-Host "`n=== T1: /api/ai/status ===" -ForegroundColor Cyan
(Invoke-RestMethod "$base/api/ai/status") | ConvertTo-Json -Depth 5 -Compress

# --- T2: real LLM ask (expect engine: llm) ---
Write-Host "`n=== T2: /api/ai/ask (LLM real test) ===" -ForegroundColor Cyan
 $b1 = @{ question = "شرایط انتقال و مهمانی دانشجو چیست؟"; domain = "regulations"; student_ref = "402101001" } | ConvertTo-Json -Compress
try {
  $resp = Invoke-RestMethod -Method Post -Uri "$base/api/ai/ask" -ContentType "application/json; charset=utf-8" -Body $b1 -TimeoutSec 180
  Write-Host ("engine          : " + $resp.engine)
  Write-Host ("low_confidence  : " + $resp.low_confidence)
  Write-Host ("latency_ms      : " + $resp.latency_ms)
  Write-Host ("sources count   : " + $resp.sources.Count)
  Write-Host ("answer (300ch)  : " + $resp.answer.Substring(0, [Math]::Min(300, $resp.answer.Length)))
  if ($resp.engine -eq "llm") {
    Write-Host "`n*** SUCCESS: REAL LLM (AvalAI) IS LIVE ***" -ForegroundColor Green
  } else {
    Write-Host "`nengine != llm -> backend logs tail:" -ForegroundColor Red
    Get-Content $out -Tail 25 -ErrorAction SilentlyContinue
    Get-Content $err -Tail 25 -ErrorAction SilentlyContinue
    Write-Host "`nHINT: check exact model id on AvalAI dashboard (e.g. gpt-5.4 vs gpt-5.4-...); edit LLM_MODEL in backend\.env and rerun." -ForegroundColor Yellow
  }
} catch {
  Write-Host ("ask FAILED: " + $_.Exception.Message) -ForegroundColor Red
  Get-Content $err -Tail 30 -ErrorAction SilentlyContinue
}
Write-Host "`n=== BLOCK A DONE ===" -ForegroundColor Green
