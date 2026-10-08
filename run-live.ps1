# Starts Watermark for the real Ring account: server, web app and the ngrok tunnel,
# each in its own window and each restarted if it exits. This window keeps the
# laptop awake and checks the public URL every minute.
# Usage: .\run-live.ps1            (live Ring account)
#        .\run-live.ps1 -Mode mock (same setup with the mock account, for checking the tunnel)
#        .\run-live.ps1 -Mode playground (Ring Developer Playground; paste a fresh token into tmp\playground_token.txt)
param([ValidateSet("live", "mock", "playground")][string]$Mode = "live")

$root = $PSScriptRoot
$py = Join-Path $root ".venv\Scripts\python.exe"
$envFile = Join-Path $root "server\.env"

$vars = @{}
foreach ($line in Get-Content $envFile) {
  if ($line -match '^\s*([A-Z_][A-Z0-9_]*)=(.*)$') { $vars[$Matches[1]] = $Matches[2].Trim() }
}
$domain = ([Uri]$vars["PUBLIC_BASE_URL"]).Host
if (-not $domain) { throw "PUBLIC_BASE_URL is empty in server\.env" }

# Live and mock keep separate databases so a mock run never mixes with real evidence.
$vars["MODE"] = $Mode
$vars["DATA_DIR"] = "data\$Mode"
$envSetup = ($vars.GetEnumerator() | ForEach-Object { "`$env:$($_.Key)='$($_.Value -replace "'", "''")'" }) -join "; "

function Start-Looped($title, $dir, $cmd) {
  # A crash or a dropped connection restarts the process after 5 s instead of leaving it down.
  $loop = "`$host.UI.RawUI.WindowTitle='$title'; cd '$dir'; $envSetup; while (`$true) { $cmd; Write-Host '$title exited, restarting in 5 s' -ForegroundColor Yellow; Start-Sleep 5 }"
  Start-Process powershell -ArgumentList "-NoExit", "-Command", $loop
}

Start-Looped "Watermark server" "$root\server" "& '$py' -m uvicorn watermark.main:app --host 127.0.0.1 --port 8765"
Start-Looped "Watermark web" "$root\web" "if (-not (Test-Path .next\BUILD_ID)) { npm run build }; npm start"
Start-Looped "Watermark tunnel" $root "ngrok http 3000 --url=$domain"

# Keep the laptop from sleeping while this window is open (released when it closes).
Add-Type -Namespace Win -Name Power -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint f);'
[Win.Power]::SetThreadExecutionState([uint32]2147483649) | Out-Null   # ES_CONTINUOUS | ES_SYSTEM_REQUIRED

$host.UI.RawUI.WindowTitle = "Watermark status"
Write-Host "Mode: $Mode    Public: https://$domain    Dashboard: https://$domain/dashboard"
Write-Host "Keep this window open. Closing it lets the laptop sleep again."
while ($true) {
  Start-Sleep 60
  try {
    $h = Invoke-RestMethod "https://$domain/health" -Headers @{ "ngrok-skip-browser-warning" = "1" } -TimeoutSec 15
    Write-Host "$(Get-Date -Format HH:mm:ss)  ok  mode=$($h.mode) open_incidents=$($h.open_incidents)"
  } catch {
    Write-Host "$(Get-Date -Format HH:mm:ss)  PUBLIC URL NOT ANSWERING: $($_.Exception.Message)" -ForegroundColor Red
  }
}
