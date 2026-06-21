Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location "$root\frontend"

if (-not (Test-Path ".\node_modules")) {
    npm install
}

npm run dev
