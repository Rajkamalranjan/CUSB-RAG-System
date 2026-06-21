Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$env:PYTHONPATH = $root
$env:VECTOR_BACKEND = if ($env:VECTOR_BACKEND) { $env:VECTOR_BACKEND } else { "qdrant" }
$env:QDRANT_PATH = if ($env:QDRANT_PATH) { $env:QDRANT_PATH } else { "data\qdrant_local" }

.\venv\Scripts\python.exe -m celery -A backend.worker.celery_app worker --loglevel=info --pool=solo
