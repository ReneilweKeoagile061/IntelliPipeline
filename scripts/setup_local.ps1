# IntelliPipeline local setup — Week 1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "IntelliPipeline local setup" -ForegroundColor Cyan

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}
& .\.venv\Scripts\Activate.ps1

pip install -r requirements-local.txt

if (-not (Test-Path ".env")) {
    Copy-Item .env.example .env
    Write-Host "Created .env from .env.example"
}

$env:INTELLIPIPELINE_LOCAL = "1"
$env:FEATURE_STORE_PATH = "data/fraud_features.csv"
$env:MLFLOW_TRACKING_URI = "file:./mlruns"

python scripts/run_local_pipeline.py

Write-Host "`nSetup complete. Start UI:" -ForegroundColor Green
Write-Host "  cd api; python app.py"
Write-Host "  cd dashboard; npm install; npm run dev"
