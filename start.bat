@echo off
setlocal

REM === Check for Python availability ===
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python is not installed or not in PATH.
    pause
    exit /b 1
)

REM === Create virtual environment if it doesn't exist ===
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo Failed to create virtual environment.
        pause
        exit /b 1
    )
)

REM === Activate the virtual environment ===
call venv\Scripts\activate.bat

REM === Upgrade pip and setuptools ===
echo Upgrading pip and setuptools...
python -m pip install --upgrade pip setuptools

REM === Install dependencies ===
echo Installing dependencies...
pip install flask pillow rembg onnxruntime

if %errorlevel% neq 0 (
    echo Failed to install dependencies.
    pause
    exit /b 1
)

REM === Run the Flask app ===
echo Running the app...
python web_bg_remover.py

REM === Deactivate the venv after exit ===
deactivate

endlocal
pause
