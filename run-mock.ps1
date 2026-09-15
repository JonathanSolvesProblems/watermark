# Starts the mock server, the web app and a simulated rover in three windows.
# Usage: .\run-mock.ps1   (from the repo root, after the install steps in README.md)
$root = $PSScriptRoot
$py = Join-Path $root ".venv\Scripts\python.exe"

Start-Process powershell -ArgumentList "-NoExit", "-Command",
  "cd '$root\server'; `$env:MODE='mock'; `$env:CAPTURE_INTERVAL_S='30'; `$env:ROVER_WAIT_S='30'; & '$py' -m uvicorn watermark.main:app --port 8765"

Start-Sleep -Seconds 3

Start-Process powershell -ArgumentList "-NoExit", "-Command",
  "cd '$root'; `$env:ROVER_SIMULATE='1'; `$env:WATERMARK_SERVER='http://localhost:8765'; & '$py' -m rover.agent"

Start-Process powershell -ArgumentList "-NoExit", "-Command",
  "cd '$root\web'; `$env:NEXT_PUBLIC_API_URL='http://localhost:8765'; if (-not (Test-Path .next)) { npm run build }; npm start"

Write-Host "server http://localhost:8765  web http://localhost:3000  (dashboard -> Simulate: sensor wet)"
