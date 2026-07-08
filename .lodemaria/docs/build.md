# Build Scripts for Lodemaria

## Building `lodemaria.exe`

The `build.ps1` script is used to build the self-contained single-file executable `lodemaria.exe`. It uses the PyInstaller tool, which converts Python scripts into standalone Windows executables.

### Usage:
```powershell
.\build.ps1
```

### Parameters:
- No parameters are needed for this script.

### Behavior and Error Handling:
The script installs the required package (`pyinstaller`) using pip. It then uses PyInstaller to create a single-file executable named `lodemaria.exe`. The `--onefile` option ensures that all Python dependencies are included in the final executable. The `--name lodemaria` option sets the name of the output executable. The `--clean` and `--noconfirm` options clean up any intermediate files and confirm the build process with user input, respectively.

### Notes:
- This script is intended for Windows users and should be run in a command prompt or PowerShell window.
- For Linux users, you can use the `build.sh` script to achieve similar results.

## Building `lodemaria`

The `build.sh` script is used to build the self-contained single-file executable `lodemaria`. It uses the PyInstaller tool, which converts Python scripts into standalone Linux executables.

### Usage:
```bash
./build.sh
```

### Parameters:
- No parameters are needed for this script.

### Behavior and Error Handling:
The script installs the required package (`pyinstaller`) using pip. It then uses PyInstaller to create a single-file executable named `lodemaria`. The `--onefile` option ensures that all Python dependencies are included in the final executable. The `--name lodemaria` option sets the name of the output executable. The `--clean` and `--noconfirm` options clean up any intermediate files and confirm the build process with user input, respectively.

### Notes:
- This script is intended for Linux users.
- For Windows users, you should use the `build.ps1` script to achieve similar results.
