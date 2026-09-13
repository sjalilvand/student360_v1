# push_updates.ps1 - one-command GitHub update
# usage: .\push_updates.ps1 "پیام کامیت"
Set-Location "D:\Projects\university-scheduler"
 $msg = if ($args.Count -gt 0) { $args[0] } else { "update: " + (Get-Date -Format "yyyy-MM-dd HH:mm") }
git add -A
 $bad = git diff --cached --name-only | Where-Object { $_ -match "^\.env$|\.db$" }
if ($bad) { Write-Host "ABORT sensitive staged: $($bad -join ', ')" -ForegroundColor Red; exit 1 }
 $null = git commit -m $msg 2>&1
git push origin main 2>&1 | ForEach-Object { Write-Host $_ }
Write-Host "PUSH DONE." -ForegroundColor Green
