"""Compatibility launcher — the application lives in the ``pythia`` package.

Usage:
    python pythia.py                # or: python -m pythia
    python pythia.py --model qwen2.5:3b --results 5
"""

from pythia.cli import main

if __name__ == "__main__":
    main()
