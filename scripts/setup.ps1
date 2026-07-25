$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot

if (-not (Test-Path "$RootDir\.env")) {
    Copy-Item "$RootDir\.env.example" "$RootDir\.env"
    Write-Host "Created .env from .env.example"
}

Write-Host "Installing frontend dependencies..."
Push-Location "$RootDir\frontend"
npm install
Pop-Location

Write-Host "Setting up backend virtual environment..."
Push-Location "$RootDir\backend"
python -m venv .venv
.\.venv\Scripts\pip install --upgrade pip
.\.venv\Scripts\pip install -r requirements.txt -r requirements-dev.txt
Pop-Location

Write-Host "Installing AI engine dependencies..."
Push-Location "$RootDir\ai-engine"
python -m venv .venv
.\.venv\Scripts\pip install --upgrade pip
.\.venv\Scripts\pip install -r requirements.txt
Pop-Location

Write-Host "Setup complete."