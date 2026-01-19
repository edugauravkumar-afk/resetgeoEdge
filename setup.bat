@echo off
REM Setup script for Windows deployment

echo Setting up GeoEdge Reset Project on Windows...

REM Create virtual environment
echo Creating virtual environment...
python -m venv .venv

REM Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install requirements
echo Installing requirements...
pip install -r requirements.txt

REM Create environment file if it doesn't exist
if not exist ".env" (
    echo Creating .env file from template...
    copy .env.example .env
    echo Please edit .env file with your database credentials and API keys
    notepad .env
)

REM Create logs directory
if not exist "logs" mkdir logs

echo Setup completed!
echo.
echo Next steps:
echo 1. Edit .env file with your credentials (opened in notepad)
echo 2. Test the script: python reset_inactive_accounts.py
echo 3. Set up Windows Task Scheduler using WINDOWS_SCHEDULER_SETUP.md
echo.
pause