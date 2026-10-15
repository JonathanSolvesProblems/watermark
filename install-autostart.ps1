# Registers a scheduled task that starts run-live.ps1 when I sign in and runs it again
# every 10 minutes. run-live.ps1 allows only one copy, so the repeat is a free re-check:
# if the supervisor ever died, the next tick brings it back. No admin rights needed.
# Remove with: Unregister-ScheduledTask -TaskName "Watermark live link" -Confirm:$false
$script = Join-Path $PSScriptRoot "run-live.ps1"
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
  -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$script`""
$logon = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$repeat = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 10)
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
  -StartWhenAvailable -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName "Watermark live link" -Action $action -Trigger $logon, $repeat `
  -Settings $settings -Principal $principal -Force | Out-Null
Write-Host "Registered 'Watermark live link': starts at sign-in, re-checks every 10 minutes."
