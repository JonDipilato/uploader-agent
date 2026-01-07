@echo off
REM Video Creator App - First Time Setup
REM Run this once to set everything up

echo ========================================
echo Video Creator App - First Time Setup
echo ========================================
echo.

REM Check Python
echo [1/4] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    echo.
    echo Please install Python first:
    echo 1. Open Microsoft Store
    echo 2. Search "Python 3.11" or "Python 3.12"
    echo 3. Click Install
    echo.
    echo OR run this command in Terminal:
    echo    winget install Python.Python.3
    echo.
    pause
    exit /b 1
)
echo OK - Python found
echo.

REM Check FFmpeg
echo [2/4] Checking FFmpeg...
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo WARNING: FFmpeg not found!
    echo.
    echo Installing FFmpeg...
    winget install Gyan.FFmpeg --accept-package-agreements --accept-source-agreements
    if errorlevel 1 (
        echo.
        echo FFmpeg installation failed. Please install manually:
        echo 1. Download from: https://ffmpeg.org/download.html
        echo 2. Extract and add to PATH
        echo.
        pause
        exit /b 1
    )
    echo FFmpeg installed successfully!
    echo.
    echo IMPORTANT: Close this window and restart your computer
    echo Then run this setup again.
    pause
    exit /b 0
)
echo OK - FFmpeg found
echo.

REM Create virtual environment
echo [3/4] Setting up Python environment...
if not exist .venv (
    python -m venv .venv
    echo Virtual environment created
) else (
    echo Virtual environment already exists
)
echo.

REM Install requirements
echo Installing required packages...
call .venv\Scripts\activate.bat
.pip install -r requirements.txt --quiet
echo.
echo Packages installed
echo.

REM Create necessary directories
echo [4/4] Creating folders...
if not exist secrets mkdir secrets
if not exist runs mkdir runs
if not exist assets mkdir assets
echo.
echo Folders created
echo.

REM Check for secrets
echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo NEXT STEP:
echo.

if not exist .streamlit\secrets.toml (
    echo 1. You need to set up YouTube login
    echo.
    echo Create this file:
    echo    .streamlit\secrets.toml
    echo.
    echo With these contents:
    echo    GOOGLE_CLIENT_ID = "your-client-id-here"
    echo    GOOGLE_CLIENT_SECRET = "your-client-secret-here"
    echo.
    echo Get these from:
    echo    https://console.cloud.google.com/apis/credentials
    echo.
) else (
    echo YouTube login already configured!
    echo.
)

echo 2. Double-click "Start App.bat" to launch
echo.
pause
