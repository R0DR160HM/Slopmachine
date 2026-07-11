# Builds dist\pythia.exe — a self-contained single-file executable.
# Usage: .\build.ps1
$ErrorActionPreference = "Stop"

if (-not (Test-Path "vendor\plantuml\*.jar")) {
    throw "vendor\plantuml\*.jar not found - place the PlantUML (MIT) jar there first."
}

pip install --quiet pyinstaller
pyinstaller --onefile --name pythia --clean --noconfirm --add-data "vendor/plantuml;vendor/plantuml" pythia.py

Write-Host ""
Write-Host "Build OK: dist\pythia.exe"
