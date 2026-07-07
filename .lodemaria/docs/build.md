# Build Scripts for Lodemaria Project

This document outlines the build scripts for the Lodemaria project, which are used to create a self-contained executable (`lodemaria.exe` on Windows and `lodemaria` on Linux).

## Scripts Overview

### build.ps1

- **Purpose**: Builds the Lodemaria project into a single-file executable for Windows.
- **Usage**: Run `.build.ps1` from PowerShell.

#### Functions and Constants

There are no public functions or constants in this script. It consists of:

- `$ErrorActionPreference`: Set to `Stop` to halt execution on any error.
- The main build logic, which includes installing PyInstaller, running it to create the executable, and printing a success message.

### build.sh

- **Purpose**: Builds the Lodemaria project into a single-file executable for Linux.
- **Usage**: Run `./build.sh` from a Bash shell.

#### Functions and Constants

There are no public functions or constants in this script. It consists of:

- `set -euo pipefail`: Ensures strict error handling, exiting on any errors or undefined variables.
- The main build logic, which includes installing PyInstaller, running it to create the executable, and printing a success message.

## Internal Logic and Algorithms

Both scripts use PyInstaller to convert the Python script (`lodemaria.py`) into a single-file executable. This process is identical across both platforms.

### Error Handling

- **build.ps1**: Halts execution if any command fails due to `$ErrorActionPreference = "Stop"`.
- **build.sh**: Exits on any error, undefined variable, or failed pipe operation.

### Side Effects

Both scripts perform the following actions:

- Install PyInstaller using `pip` if it's not already installed.
- Run PyInstaller with options to create a single-file executable (`--onefile`) and specify the name of the output file.
- Print a success message indicating that the build was completed successfully.

## Usage Notes

- **Windows**: Use `build.ps1` for Windows platforms. This will generate a `.exe` file in the `dist` directory.
- **Linux**: Use `build.sh` for Linux platforms. This will generate an ELF executable in the `dist` directory.

These scripts provide a straightforward way to build the Lodemaria project into a standalone executable, facilitating distribution and deployment across different operating systems.
