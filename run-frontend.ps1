$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

if (Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue) {
    throw 'Port 5173 is already in use. Stop the existing frontend before starting this WildTrack map.'
}

npm.cmd run dev -- --host 127.0.0.1 --port 5173 --strictPort
