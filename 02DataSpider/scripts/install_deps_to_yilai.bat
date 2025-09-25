@echo off
REM NeuroTrade Nexus - Module 2 Dependencies Installation Script
REM Install to D:\YiLai\pydeps directory
REM Environment Standard: Python 3.11 LTS

setlocal enabledelayedexpansion

echo === NeuroTrade Nexus Module 2 Dependencies Installation ===
echo Target Directory: D:\YiLai\pydeps
echo Python Version Requirement: 3.11 LTS

REM Check Python version
python --version
if errorlevel 1 (
    echo ERROR: Python not found in PATH
    exit /b 1
)

REM Create target directory
set "TARGET_DIR=D:\YiLai\pydeps"
if not exist "%TARGET_DIR%" (
    echo Creating directory: %TARGET_DIR%
    mkdir "%TARGET_DIR%"
) else (
    echo Directory exists: %TARGET_DIR%
    if "%1"=="--force" (
        echo Force mode: Cleaning existing dependencies...
        rmdir /s /q "%TARGET_DIR%" 2>nul
        mkdir "%TARGET_DIR%"
    )
)

REM Check requirements.txt
if not exist "requirements.txt" (
    echo ERROR: requirements.txt not found
    exit /b 1
)

echo Starting dependency installation to: %TARGET_DIR%

REM Install dependencies with binary-only constraint
python -m pip install --only-binary=:all: --target="%TARGET_DIR%" --upgrade --no-deps -r requirements.txt

if errorlevel 1 (
    echo ERROR: Dependency installation failed
    echo Suggestions:
    echo 1. Check Python version is 3.11
    echo 2. Check network connectivity
    echo 3. Check disk space
    exit /b 1
)

echo Dependencies installation completed!

REM Count installed packages
for /f %%i in ('dir /ad /b "%TARGET_DIR%" ^| find /c /v ""') do set "PKG_COUNT=%%i"
echo Installed packages count: !PKG_COUNT!

echo === Installation Complete ===
echo Please ensure application entry has configured: sys.path.insert(0, '%TARGET_DIR%')