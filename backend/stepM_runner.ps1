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

Write-Host "`n=== T1: regulations/ask (expect ai_engine=llm + answer replaced) ===" -ForegroundColor Cyan
try {
  $r = Invoke-RestMethod -Method Post -Uri "$base/api/student360/regulations/ask" -Headers $h -ContentType "application/json; charset=utf-8" -Body '{"question":"شرایط انتقال و مهمانی دانشجو چیست؟"}' -TimeoutSec 180
  Write-Host ("  ai_engine=" + $r.ai_engine + " | ai_replaced=" + $r.ai_replaced + " | low_conf=" + $r.ai_low_confidence + " | sources=" + $r.ai_sources.Count)
  $ansKey = if ($r.answer) { "answer" } elseif ($r.response) { "response" } else { "(other)" }
  if ($r.answer) { Write-Host ("  answer[:350]: " + $r.answer.Substring(0, [Math]::Min(350, $r.answer.Length))) }
  elseif ($r.response) { Write-Host ("  response[:350]: " + $r.response.Substring(0, [Math]::Min(350, $r.response.Length))) }
  else { Write-Host "  response keys: " + (($r.PSObject.Properties.Name) -join ", ") }
} catch { Write-Host ("  FAILED: " + $_.Exception.Message) -ForegroundColor Red; if ($_.ErrorDetails.Message) { Write-Host $_.ErrorDetails.Message } }

Write-Host "`n=== T2: professor/ask (expect ai fields; 422 reveals schema) ===" -ForegroundColor Cyan
try {
  $r2 = Invoke-RestMethod -Method Post -Uri "$base/api/student360/professor/ask" -Headers $h -ContentType "application/json; charset=utf-8" -Body '{"question":"یک تمرین ساده درباره حلقه for در پایتون بده"}' -TimeoutSec 180
  Write-Host ("  ai_engine=" + $r2.ai_engine + " | ai_replaced=" + $r2.ai_replaced)
  $r2 | ConvertTo-Json -Compress -Depth 3 | ForEach-Object { $_.Substring(0, [Math]::Min(700, $_.Length)) }
} catch { Write-Host ("  FAILED: " + $_.Exception.Message) -ForegroundColor Yellow; if ($_.ErrorDetails.Message) { Write-Host ("  detail: " + $_.ErrorDetails.Message.Substring(0, [Math]::Min(400, $_.ErrorDetails.Message.Length))) } }

Write-Host "`n=== T3: sanity ===" -ForegroundColor Cyan
 $oa = Invoke-RestMethod "$base/openapi.json" -TimeoutSec 5
Write-Host ("  endpoints: " + @($oa.paths.PSObject.Properties.Name).Count)

Write-Host "`n=== T4: DUMP RegulationsPage + ProfessorPage (for UI polish next) ===" -ForegroundColor Cyan
 $src = Get-Content "$be\..\frontend\src\pages\student360\Student360Pages.jsx" -Raw
foreach ($fname in @("RegulationsPage","ProfessorPage")) {
  $start = $src.IndexOf("function $fname")
  if ($start -ge 0) {
    $next = $src.IndexOf("export function", $start + 10)
    if ($next -lt 0) { $next = [Math]::Min($start + 4000, $src.Length) }
    Write-Host "`n----- $fname -----"
    Write-Host $src.Substring($start, [Math]::Min($next - $start, 4500))
  } else { Write-Host "  $fname not found" -ForegroundColor Yellow }
}

Write-Host "`n=== T5: professor route signature ===" -ForegroundColor Cyan
(Select-String -Path "$be\app\api\routes_student360.py" -Pattern "professor/ask" -Context 2,12) | ForEach-Object {
  $_.Context.PreContext; $_.Line; $_.Context.PostContext }

Write-Host "`n=== BLOCK M DONE ===" -ForegroundColor Green
