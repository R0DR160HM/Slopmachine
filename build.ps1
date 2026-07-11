# Builds dist\pythia.exe — a self-contained single-file executable.
# Usage: .\build.ps1
$ErrorActionPreference = "Stop"

pip install --quiet pyinstaller
pyinstaller --onefile --name pythia --clean --noconfirm pythia.py

Write-Host ""
Write-Host "Build OK: dist\pythia.exe"
