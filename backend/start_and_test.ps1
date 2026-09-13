# ===== start_and_test.ps1 (auto port + functional tests) =====
 $be = "D:\Projects\university-scheduler\backend"
 $ProgressPreference = 'SilentlyContinue'

function Test-OurApp([int]$prt) {
    try {
        $oa = Invoke-RestMethod "http://127.0.0.1:$prt/openapi.json" -TimeoutSec 3
        return ($oa.info.title -eq "Intelligent University Scheduler")
    } catch { return $false }
}

 $port = $null; $already = $false
 $candidates = @(8000) + @(8002..8010) + @(8765..8785)
foreach ($p in $candidates) {
    if (Test-OurApp $p) { $port = $p; $already = $true; break }
    if (-not (Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue)) { $port = $p; break }
}
if ($null -eq $port) { Write-Host "NO FREE PORT FOUND!" -ForegroundColor Red; return }

Write-Host ("Port selected: $port" + $(if ($already) {" (our app already running - reuse)"} else {" (free)"})) -ForegroundColor Cyan

if (-not $already) {
    $py = "$be\.venv\Scripts\python.exe"
    if (-not (Test-Path $py)) { $py = "python" }
    $out = "$be\.runtime.out.log"; $err = "$be\.runtime.err.log"
    Remove-Item $out, $err -ErrorAction SilentlyContinue
    Start-Process -FilePath $py -ArgumentList @("-m","uvicorn","app.main:app","--host","127.0.0.1","--port","$port") -WorkingDirectory $be -WindowStyle Hidden -RedirectStandardOutput $out -RedirectStandardError $err
    Write-Host "Backend starting (hidden) - logs: $err"
}

 $ready = $false
foreach ($i in 1..30) { Start-Sleep -Seconds 2; if (Test-OurApp $port) { $ready = $true; break } }
if (-not $ready) {
    Write-Host "BACKEND NOT READY - last log lines:" -ForegroundColor Red
    Get-Content "$be\.runtime.err.log" -Tail 30 -ErrorAction SilentlyContinue
    Get-Content "$be\.runtime.out.log" -Tail 10 -ErrorAction SilentlyContinue
    return
}

 $base = "http://127.0.0.1:$port"
Set-Content -LiteralPath "$be\.runtime_port" -Value "$port"
Write-Host "READY: $base" -ForegroundColor Green

 $oa  = Invoke-RestMethod "$base/openapi.json" -TimeoutSec 5
 $paths = @($oa.paths.PSObject.Properties.Name)
Write-Host ("Total endpoints: " + $paths.Count)
Write-Host "--- /api/events paths ---"
 $paths | Where-Object { $_ -match "/api/events" } | ForEach-Object { Write-Host ("  " + $_) }

Write-Host "`n=== TEST 1: OTP (pilot student 402101001) ===" -ForegroundColor Cyan
 $otpPath = $paths | Where-Object { $_ -match "otp/request" } | Select-Object -First 1
Write-Host ("  path: " + $otpPath)
try {
    $r = Invoke-RestMethod -Method Post -Uri ("$base" + $otpPath) -ContentType "application/json" -Body '{"student_number":"402101001"}' -TimeoutSec 10
    Write-Host ("  OTP OK: " + ($r | ConvertTo-Json -Compress -Depth 4)) -ForegroundColor Green
} catch {
    Write-Host ("  OTP FAILED: " + $_.Exception.Message) -ForegroundColor Red
    if ($_.ErrorDetails.Message) { Write-Host ("    detail: " + $_.ErrorDetails.Message) }
}

Write-Host "`n=== TEST 2: POST 3 events ===" -ForegroundColor Cyan
 $i = 0
foreach ($e in @(@{t="login";n="pilot login"},@{t="regulation_ask";n="rules question"},@{t="quiz_submitted";n="quiz #1"})) {
    $i++
    $b = @{ event_type=$e.t; event_name=$e.n; student_ref="402101001"; session_ref="ps-test"; source="api"; payload=@{step=$i} } | ConvertTo-Json -Compress
    try {
        $r = Invoke-RestMethod -Method Post -Uri "$base/api/events" -ContentType "application/json" -Body $b -TimeoutSec 10
        Write-Host ("  event #$i OK -> id " + $r.event.id) -ForegroundColor Green
    } catch {
        Write-Host ("  event #$i FAILED: " + $_.Exception.Message) -ForegroundColor Red
        if ($_.ErrorDetails.Message) { Write-Host ("    detail: " + $_.ErrorDetails.Message) }
    }
}

Write-Host "`n=== TEST 3: EVENTS SUMMARY ===" -ForegroundColor Cyan
try { (Invoke-RestMethod "$base/api/events/summary?days=30" -TimeoutSec 10) | ConvertTo-Json -Compress -Depth 5 } catch { Write-Host ("  summary FAILED: " + $_.Exception.Message) -ForegroundColor Red }

Write-Host "`n=== TEST 4: RECENT (top 5) ===" -ForegroundColor Cyan
try {
    $rec = Invoke-RestMethod "$base/api/events/recent?limit=5" -TimeoutSec 10
    $rec | ForEach-Object { Write-Host ("  #" + $_.id + " | " + $_.event_type + " | " + $_.student_ref + " | " + $_.occurred_at) }
} catch { Write-Host ("  recent FAILED: " + $_.Exception.Message) -ForegroundColor Red }

Write-Host "`n=== ALL DONE ===" -ForegroundColor Green
