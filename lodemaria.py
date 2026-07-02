"""Compatibility launcher — the application lives in the ``lodemaria`` package.

Usage:
    python lodemaria.py                # or: python -m lodemaria
    python lodemaria.py --model qwen2.5:3b --results 5
"""

from lodemaria.cli import main

if __name__ == "__main__":
    main()
