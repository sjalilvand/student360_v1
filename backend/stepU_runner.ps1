 $be = "D:\Projects\university-scheduler\backend"
 $env:PYTHONIOENCODING = "utf-8"
 $py = "$be\.venv\Scripts\python.exe"
 $ProgressPreference = 'SilentlyContinue'
if (-not (Test-Path $py)) { Write-Host "venv python missing" -ForegroundColor Red; return }
& $py -c "import sqlalchemy" 2>$null
if ($LASTEXITCODE -ne 0) { Write-Host "WRONG VENV - abort" -ForegroundColor Red; return }

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
 $h = @{ "X-Student-Number" = "402101001"; "Content-Type" = "application/json" }

Write-Host "`n=== T1: generate quiz CS201 (first time -> medium) ===" -ForegroundColor Cyan
 $b = '{"course_code":"CS201"}'
 $q = Invoke-RestMethod -Method Post -Uri "$base/api/adaptive-quiz/next" -Headers $h -Body $b -TimeoutSec 180
Write-Host ("  quiz_id=" + $q.quiz_id + " | level=" + $q.level + " (" + $q.level_label + ") | source=" + $q.source + " | questions=" + $q.questions.Count)
 $q.questions | ForEach-Object { Write-Host ("    Q" + ($_.index+1) + ": " + $_.question.Substring(0, [Math]::Min(80, $_.question.Length))) }

Write-Host "`n=== T2: submit (all zeros -> expect low score) ===" -ForegroundColor Cyan
 $ans = @(0,0,0,0)
 $bsub = '{"answers":[0,0,0,0]}'
 $r = Invoke-RestMethod -Method Post -Uri "$base/api/adaptive-quiz/$($q.quiz_id)/submit" -Headers $h -Body $bsub -TimeoutSec 30
Write-Host ("  score=" + $r.score_pct + "% | correct=" + $r.correct_count + "/" + $r.total + " | next_level=" + $r.next_level_label)

Write-Host "`n=== T3: generate again (level should adapt DOWN if score<50) ===" -ForegroundColor Cyan
 $q2 = Invoke-RestMethod -Method Post -Uri "$base/api/adaptive-quiz/next" -Headers $h -Body $b -TimeoutSec 180
Write-Host ("  new level=" + $q2.level_label + " | source=" + $q2.source)

Write-Host "`n=== T4: history ===" -ForegroundColor Cyan
(Invoke-RestMethod "$base/api/adaptive-quiz/history" -Headers @{ "X-Student-Number" = "402101001" } -TimeoutSec 15).items | ForEach-Object {
  Write-Host ("    " + $_.course_code + " | " + $_.level + " | " + $_.score_pct + "%")
}

Write-Host "`n=== T5: JSX compile ===" -ForegroundColor Cyan
foreach ($f in @("Student360Portal.jsx","AdaptiveQuizPage.jsx")) {
  try { $r = Invoke-WebRequest "http://127.0.0.1:5173/src/pages/student360/$f" -TimeoutSec 10 -UseBasicParsing; Write-Host ("  $f -> OK") -ForegroundColor Green }
  catch { Write-Host ("  $f -> COMPILE ERROR") -ForegroundColor Red }
}

Write-Host "`n=== T6: sanity ===" -ForegroundColor Cyan
 $oa = Invoke-RestMethod "$base/openapi.json" -TimeoutSec 5
Write-Host ("  endpoints: " + @($oa.paths.PSObject.Properties.Name).Count)

Write-Host "`n=== BLOCK U DONE ===" -ForegroundColor Green
