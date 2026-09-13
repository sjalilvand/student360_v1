# push_updates.ps1 - one-command GitHub update
# usage: .\push_updates.ps1 "commit message"
Set-Location "D:\Projects\university-scheduler"
 $msg = if ($args.Count -gt 0) { $args[0] } else { "update: " + (Get-Date -Format "yyyy-MM-dd HH:mm") }
git add -A
# block only ADD/MODIFY of sensitive files (their deletion is desired)
 $bad = git diff --cached --name-only --diff-filter=ACMR | Where-Object { $_ -match "^\.env$|\.db$|\.sqlite$" }
if ($bad) { Write-Host "ABORT sensitive staged: $($bad -join ', ')" -ForegroundColor Red; exit 1 }
 $null = git commit -m $msg 2>&1
git push origin main 2>&1 | ForEach-Object { Write-Host $_ }
if ($LASTEXITCODE -eq 0) { Write-Host "PUSH DONE." -ForegroundColor Green } else { Write-Host "PUSH FAILED." -ForegroundColor Red }
