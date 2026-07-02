# Builds dist\lodemaria.exe — a self-contained single-file executable.
# Usage: .\build.ps1
$ErrorActionPreference = "Stop"

pip install --quiet pyinstaller
pyinstaller --onefile --name lodemaria --clean --noconfirm lodemaria.py

Write-Host ""
Write-Host "Build OK: dist\lodemaria.exe"
