# Keeps Watermark's public link up: the server, the web app and the ngrok tunnel, each
# checked every 30 s and restarted if it is down or stops answering. Everything runs
# hidden with logs in logs\, so there is no window to close by accident. Only one copy
# runs at a time, and a scheduled task (install-autostart.ps1) starts it at sign-in and
# re-checks every 10 minutes, so a restart or a crash brings the link back by itself.
#
# Usage: .\run-live.ps1                  (mode from logs\mode.txt, else mock)
#        .\run-live.ps1 -Mode live       (real Ring account; the choice is remembered)
#        .\run-live.ps1 -Mode playground (paste a fresh token into tmp\playground_token.txt)
#        .\run-live.ps1 -Stop            (stop everything, including the supervisor)
param([ValidateSet("", "live", "mock", "playground")][string]$Mode = "", [switch]$Stop)

$root = $PSScriptRoot
$logs = Join-Path $root "logs"
New-Item -ItemType Directory -Force $logs | Out-Null
$modeFile = Join-Path $logs "mode.txt"
$pidFile = Join-Path $logs "pids.json"

function Stop-Component($procId) {
  # Kill the hidden shell and everything it started (uvicorn, node, ngrok).
  if ($procId) { & taskkill /PID $procId /T /F 2>$null | Out-Null }
}

if ($Stop) {
  if (Test-Path $pidFile) {
    (Get-Content $pidFile -Raw | ConvertFrom-Json).PSObject.Properties | ForEach-Object { Stop-Component $_.Value }
    Remove-Item $pidFile
  }
  Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" |
    Where-Object { $_.CommandLine -match 'run-live\.ps1' -and $_.ProcessId -ne $PID } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
  # Parts the supervisor adopted rather than started (an older copy already serving) are
  # not in pids.json, so also clear whatever holds the two ports, and the tunnel.
  foreach ($port in 8765, 3000) {
    Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
      ForEach-Object { Stop-Component $_.OwningProcess }
  }
  Get-Process ngrok -ErrorAction SilentlyContinue | ForEach-Object { Stop-Component $_.Id }
  Write-Host "Watermark stopped."
  return
}

# One supervisor at a time: a second copy (the scheduled re-check) exits straight away.
$mutex = New-Object Threading.Mutex($false, "Local\WatermarkLiveSupervisor")
if (-not $mutex.WaitOne(0)) { return }

if ($Mode) { Set-Content $modeFile $Mode -Encoding ascii }
$Mode = if (Test-Path $modeFile) { (Get-Content $modeFile -Raw).Trim() } else { "mock" }

$py = Join-Path $root ".venv\Scripts\python.exe"
$vars = @{}
foreach ($line in Get-Content (Join-Path $root "server\.env")) {
  if ($line -match '^\s*([A-Z_][A-Z0-9_]*)=(.*)$') { $vars[$Matches[1]] = $Matches[2].Trim() }
}
$domain = ([Uri]$vars["PUBLIC_BASE_URL"]).Host
if (-not $domain) { throw "PUBLIC_BASE_URL is empty in server\.env" }
# Live, mock and playground keep separate databases so a test never mixes with real evidence.
$vars["MODE"] = $Mode
$vars["DATA_DIR"] = "data\$Mode"
$envSetup = ($vars.GetEnumerator() | ForEach-Object { "`$env:$($_.Key)='$($_.Value -replace "'", "''")'" }) -join "; "

$parts = [ordered]@{
  server = @{ dir = "$root\server"; cmd = "& '$py' -m uvicorn watermark.main:app --host 127.0.0.1 --port 8765" }
  web    = @{ dir = "$root\web"; cmd = "if (-not (Test-Path .next\BUILD_ID)) { npm run build }; npm start" }
  tunnel = @{ dir = $root; cmd = "ngrok http 3000 --url=$domain --log=stdout" }
}

function Start-Component($name) {
  $p = $parts[$name]
  $log = Join-Path $logs "$name.log"
  $inner = "cd '$($p.dir)'; $envSetup; $($p.cmd) *>> '$log'"
  $proc = Start-Process powershell -WindowStyle Hidden -PassThru `
    -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $inner
  "$(Get-Date -Format s)  started $name (pid $($proc.Id))" | Add-Content (Join-Path $logs "supervisor.log")
  return $proc.Id
}

function Test-Component($name) {
  try {
    switch ($name) {
      "server" { return [bool](Invoke-RestMethod "http://127.0.0.1:8765/health" -TimeoutSec 10) }
      "web"    { return (Invoke-WebRequest "http://127.0.0.1:3000/" -UseBasicParsing -TimeoutSec 20).StatusCode -eq 200 }
      "tunnel" { return [bool](Invoke-RestMethod "https://$domain/health" -Headers @{ "ngrok-skip-browser-warning" = "1" } -TimeoutSec 20) }
    }
  } catch { return $false }
}

# Keep the laptop from sleeping for as long as the supervisor runs.
Add-Type -Namespace Win -Name Power -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint f);'
[Win.Power]::SetThreadExecutionState([uint32]2147483649) | Out-Null   # ES_CONTINUOUS | ES_SYSTEM_REQUIRED

$pids = @{}
$fails = @{ server = 0; web = 0; tunnel = 0 }
# Grace after a (re)start before a failed check counts: the web build can take minutes.
$grace = @{ server = 0; web = 0; tunnel = 0 }
"$(Get-Date -Format s)  supervisor up, mode=$Mode, public https://$domain" | Add-Content (Join-Path $logs "supervisor.log")

while ($true) {
  foreach ($name in $parts.Keys) {
    $alive = $pids[$name] -and (Get-Process -Id $pids[$name] -ErrorAction SilentlyContinue)
    if (-not $alive) {
      # Anything already serving the port (an older copy) is reused, not duplicated.
      if (Test-Component $name) { $fails[$name] = 0; continue }
      $pids[$name] = Start-Component $name
      $grace[$name] = if ($name -eq "web") { 20 } else { 4 }
      $fails[$name] = 0
      continue
    }
    if ($grace[$name] -gt 0) { $grace[$name]--; continue }
    if (Test-Component $name) { $fails[$name] = 0; continue }
    $fails[$name]++
    # Three failed checks in a row (90 s) means hung, not slow: restart it.
    if ($fails[$name] -ge 3) {
      "$(Get-Date -Format s)  $name not answering, restarting" | Add-Content (Join-Path $logs "supervisor.log")
      Stop-Component $pids[$name]
      $pids[$name] = $null
    }
  }
  $pids | ConvertTo-Json | Set-Content $pidFile
  $state = ($parts.Keys | ForEach-Object { "$_=$(if ($fails[$_] -eq 0) { 'ok' } else { "fail$($fails[$_])" })" }) -join " "
  Set-Content (Join-Path $logs "status.txt") "$(Get-Date -Format s)  mode=$Mode  $state  https://$domain"
  Start-Sleep 30
}
