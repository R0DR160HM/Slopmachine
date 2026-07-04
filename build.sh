#!/usr/bin/env bash
# Builds dist/lodemaria — a self-contained single-file executable (Linux ELF).
# Usage: ./build.sh
#
# Note: PyInstaller is not a cross-compiler. This produces a Linux binary that
# runs only on Linux; use build.ps1 on Windows to produce dist/lodemaria.exe.
set -euo pipefail

pip install --quiet pyinstaller
pyinstaller --onefile --name lodemaria --clean --noconfirm lodemaria.py

echo
echo "Build OK: dist/lodemaria"
