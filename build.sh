#!/usr/bin/env bash
# Builds dist/pythia — a self-contained single-file executable (Linux ELF).
# Usage: ./build.sh
#
# Note: PyInstaller is not a cross-compiler. This produces a Linux binary that
# runs only on Linux; use build.ps1 on Windows to produce dist/pythia.exe.
set -euo pipefail

pip install --quiet pyinstaller
pyinstaller --onefile --name pythia --clean --noconfirm pythia.py

echo
echo "Build OK: dist/pythia"
