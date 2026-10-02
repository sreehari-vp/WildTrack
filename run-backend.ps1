$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

if (Get-NetTCPConnection -LocalPort 8001 -State Listen -ErrorAction SilentlyContinue) {
    throw 'Port 8001 is already in use. Stop the existing backend before starting this WildTrack API.'
}

& (Join-Path $PSScriptRoot 'backend\venv\Scripts\python.exe') -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8001
