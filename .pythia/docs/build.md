# **build.ps1**

This PowerShell script builds the `dist\pythia.exe` executable, a self-contained single-file executable. It uses PyInstaller to compile the Python code into a standalone executable.

### Parameters:
- None

### Return Values:
- The script exits with status 0 if the build is successful.

### Behavior and Error Handling:
1. **Error Handling**: The `$ErrorActionPreference` is set to `Stop`, ensuring that any errors during the execution of the script will stop the script execution.
2. **Pip Installation**: The `pip install --quiet pyinstaller` command installs PyInstaller quietly, reducing verbosity.
3. **PyInstaller Execution**: The `pyinstaller --onefile --name pythia --clean --noconfirm pythia.py` command builds the executable with the specified parameters:
   - `--onefile`: Creates a single-file executable.
   - `--name pythia`: Sets the name of the output file to `pythia`.
   - `--clean`: Cleans up after the build process, removing temporary files and directories.
   - `--noconfirm`: Does not prompt for confirmation before proceeding with the build.

### Output:
```
Build OK: dist\pythia.exe
```

### Notes:
- PyInstaller is not a cross-compiler. This script produces a Linux binary that runs only on Linux; use `build.ps1` on Windows to produce `dist/pythia.exe`.

---

# **build.sh**

This shell script builds the `dist/pythia` executable, a self-contained single-file executable (Linux ELF).

### Parameters:
- None

### Return Values:
- The script exits with status 0 if the build is successful.

### Behavior and Error Handling:
1. **Error Handling**: The `set -euo pipefail` command ensures that any errors during the execution of the script will stop the script execution.
2. **Pip Installation**: The `pip install --quiet pyinstaller` command installs PyInstaller quietly, reducing verbosity.
3. **PyInstaller Execution**: The `pyinstaller --onefile --name pythia --clean --noconfirm pythia.py` command builds the executable with the specified parameters:
   - `--onefile`: Creates a single-file executable.
   - `--name pythia`: Sets the name of the output file to `pythia`.
   - `--clean`: Cleans up after the build process, removing temporary files and directories.
   - `--noconfirm`: Does not prompt for confirmation before proceeding with the build.

### Output:
```
Build OK: dist/pythia
```
