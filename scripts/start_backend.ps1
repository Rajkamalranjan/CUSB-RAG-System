Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path ".\venv\Scripts\python.exe")) {
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create virtual environment."
    }
}

.\venv\Scripts\python.exe -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install core requirements."
}

$env:PYTHONPATH = $root
$env:VECTOR_BACKEND = "faiss"
$env:QDRANT_PATH = if ($env:QDRANT_PATH) { $env:QDRANT_PATH } else { "data\qdrant_local" }

.\venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8080
