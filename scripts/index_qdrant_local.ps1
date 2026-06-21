Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$env:PYTHONPATH = $root
$env:QDRANT_PATH = if ($env:QDRANT_PATH) { $env:QDRANT_PATH } else { "data\qdrant_local" }

.\venv\Scripts\python.exe scripts\index_qdrant.py
