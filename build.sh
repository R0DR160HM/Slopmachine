#!/usr/bin/env bash
# Builds dist/pythia — a self-contained single-file executable (Linux ELF).
# Usage: ./build.sh
#
# Note: PyInstaller is not a cross-compiler. This produces a Linux binary that
# runs only on Linux; use build.ps1 on Windows to produce dist/pythia.exe.
set -euo pipefail

if ! ls vendor/plantuml/*.jar >/dev/null 2>&1; then
  echo "vendor/plantuml/*.jar not found — place the PlantUML (MIT) jar there first." >&2
  exit 1
fi

pip install --quiet pyinstaller
pyinstaller --onefile --name pythia --clean --noconfirm \
  --add-data "vendor/plantuml:vendor/plantuml" pythia.py

echo
echo "Build OK: dist/pythia"
