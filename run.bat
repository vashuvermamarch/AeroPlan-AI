@echo off
echo ==================================================
echo Starting AeroPlan AI Travel Booking System...
echo ==================================================

REM Check if Python is installed
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python was not found on your system. Please install Python and try again.
    pause
    exit /b 1
)

REM Check if venv directory exists
if exist venv goto activate_venv

echo Creating virtual environment (venv)...
python -m venv venv
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
)

echo Activating venv and installing requirements...
call venv\Scripts\activate.bat
pip install -r requirement.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)
goto run_app

:activate_venv
echo Activating virtual environment...
call venv\Scripts\activate.bat

:run_app
echo Starting Streamlit app...
streamlit run frontend.py
pause
