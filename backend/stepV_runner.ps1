 $be = "D:\Projects\university-scheduler\backend"
 $fe = "D:\Projects\university-scheduler\frontend"
 $env:PYTHONIOENCODING = "utf-8"
 $py = "$be\.venv\Scripts\python.exe"
 $ProgressPreference = 'SilentlyContinue'
if (-not (Test-Path $py)) { Write-Host "venv python missing" -ForegroundColor Red; return }
& $py -c "import sqlalchemy" 2>$null
if ($LASTEXITCODE -ne 0) { Write-Host "WRONG VENV - abort" -ForegroundColor Red; return }

Write-Host "=== T1: portal content grep (imports + menus must exist) ===" -ForegroundColor Cyan
 $src = Get-Content "$fe\src\pages\student360\Student360Portal.jsx" -Raw
foreach ($needle in @('import StudyPathPage', 'import AdaptiveQuizPage', 'id: "studypath"', 'id: "adaptivequiz"', 'studypath: <StudyPathPage />', 'adaptivequiz: <AdaptiveQuizPage />')) {
  if ($src.Contains($needle)) { Write-Host ("  OK   : " + $needle) -ForegroundColor Green }
  else { Write-Host ("  MISS : " + $needle) -ForegroundColor Red }
}

Write-Host "`n=== T2: JSX compile via Vite ===" -ForegroundColor Cyan
foreach ($f in @("Student360Portal.jsx","AdaptiveQuizPage.jsx","StudyPathPage.jsx")) {
  try { $r = Invoke-WebRequest "http://127.0.0.1:5173/src/pages/student360/$f" -TimeoutSec 10 -UseBasicParsing; Write-Host ("  $f -> OK") -ForegroundColor Green }
  catch { Write-Host ("  $f -> COMPILE ERROR: " + $_.Exception.Message) -ForegroundColor Red }
}

Write-Host "`n=== T3: backend sanity ===" -ForegroundColor Cyan
try {
  $oa = Invoke-RestMethod "http://127.0.0.1:8000/openapi.json" -TimeoutSec 5
  Write-Host ("  endpoints: " + @($oa.paths.PSObject.Properties.Name).Count)
  (Invoke-RestMethod "http://127.0.0.1:8000/health" -TimeoutSec 5) | ConvertTo-Json -Compress
} catch { Write-Host "  backend down - restart with any runner" -ForegroundColor Yellow }

Write-Host "`n=== BLOCK V DONE ===" -ForegroundColor Green
