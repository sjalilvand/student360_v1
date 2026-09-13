 $be = "D:\Projects\university-scheduler\backend"
 $env:PYTHONIOENCODING = "utf-8"
 $py = "$be\.venv\Scripts\python.exe"
 $ProgressPreference = 'SilentlyContinue'
if (-not (Test-Path $py)) { Write-Host "venv python missing" -ForegroundColor Red; return }
& $py -c "import sqlalchemy, pytest" 2>$null
if ($LASTEXITCODE -ne 0) { Write-Host "WRONG VENV - abort" -ForegroundColor Red; return }

Write-Host "=== T0: KEY ROTATION VERIFY (no key printed) ===" -ForegroundColor Cyan
 $key = ((Get-Content "$be\.env") | Where-Object { $_ -like "OPENAI_API_KEY=*" }) -replace "^OPENAI_API_KEY=", ""
 $old = "aa-54M0OVztxPwkGlowXkYbDuzOHeNLZTPMUJZcxdHR7ug2IKrP"
if ([string]::IsNullOrWhiteSpace($key)) { Write-Host "  NO KEY in .env!" -ForegroundColor Red }
elseif ($key -eq $old) { Write-Host "  ⚠️ STILL THE OLD EXPOSED KEY - revoke in panel & replace!" -ForegroundColor Red }
else { Write-Host "  key differs from the exposed one ✔ (len $($key.Length))" -ForegroundColor Green }

Write-Host "`n=== T1: pytest (expect 18 passed) ===" -ForegroundColor Cyan
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
 $h = @{ "X-Student-Number" = "402101001"; "Content-Type" = "application/json" }

Write-Host "`n=== T3: LLM live with (new?) key ===" -ForegroundColor Cyan
try {
  $st = Invoke-RestMethod "$base/api/ai/status" -TimeoutSec 10
  Write-Host ("  enabled=" + $st.llm.enabled)
} catch { Write-Host ("  status fail: " + $_.Exception.Message) -ForegroundColor Red }

Write-Host "`n=== T4: twin simulate GOOD term (Ali, 12u avg 16) ===" -ForegroundColor Cyan
try {
  $b = '{"courses":[{"title":"هوش مصنوعی","credits":3,"expected_grade":17},{"title":"شبکه","credits":3,"expected_grade":16},{"title":"کارآموزی","credits":3,"expected_grade":18},{"title":"پایگاه داده","credits":3,"expected_grade":15}]}'
  $r = Invoke-RestMethod -Method Post -Uri "$base/api/twin/simulate" -Headers $h -Body $b -TimeoutSec 30
  Write-Host ("  term_gpa=" + $r.scenario.term_gpa + " | GPA " + $r.before.gpa + " -> " + $r.after.gpa + " | risk " + $r.before.risk_score + " -> " + $r.after.risk_score + " | cap " + $r.before.max_units + " -> " + $r.after.max_units)
  Write-Host ("  skills: " + (($r.skill_preview.PSObject.Properties | ForEach-Object { $_.Name + "=>" + ($_.Value -join "/") }) -join " | "))
} catch { Write-Host ("  FAIL: " + $_.Exception.Message) -ForegroundColor Red; if ($_.ErrorDetails.Message) { Write-Host $_.ErrorDetails.Message } }

Write-Host "`n=== T5: twin simulate BAD term (12u avg 9) ===" -ForegroundColor Cyan
try {
  $b2 = '{"units":12,"avg_grade":9}'
  $r2 = Invoke-RestMethod -Method Post -Uri "$base/api/twin/simulate" -Headers $h -Body $b2 -TimeoutSec 30
  Write-Host ("  probation " + $r2.before.probation_count + " -> " + $r2.after.probation_count + " | cap " + $r2.before.max_units + " -> " + $r2.after.max_units + " | warnings=" + $r2.warnings.Count)
} catch { Write-Host ("  FAIL: " + $_.Exception.Message) -ForegroundColor Red }

Write-Host "`n=== T6: sanity ===" -ForegroundColor Cyan
 $oa = Invoke-RestMethod "$base/openapi.json" -TimeoutSec 5
Write-Host ("  endpoints: " + @($oa.paths.PSObject.Properties.Name).Count)
(Invoke-RestMethod "$base/health") | ConvertTo-Json -Compress

Write-Host "`n=== BLOCK AF DONE ===" -ForegroundColor Green
