@echo off
:: Setup script for LUNA on Windows systems

echo Setting up LUNA project...

:: Check if Python is installed
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Python is not installed. Please install Python before continuing.
    exit /b 1
)

:: Create virtual environment if it doesn't exist
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
) else (
    echo Virtual environment already exists.
)

:: Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

:: Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

echo Setup complete!
echo.
echo To activate the environment in your terminal, run:
echo venv\Scripts\activate.bat
echo.
echo To run the project, ensure your .env.local file is set up, then run:
echo python main.py --init       # To initialize database schema
echo python main.py --create-example   # To create an example workflow
echo python main.py --run        # To run the workflow

:: Keep the window open
pause 