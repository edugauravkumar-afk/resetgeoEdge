@echo off
REM Daily GeoEdge Reset Script Runner for Windows
REM This script runs the reset inactive accounts process daily

REM Set script directory (update this path for your Windows system)
set SCRIPT_DIR=C:\path\to\geoedge-country-projects
set LOG_DIR=%SCRIPT_DIR%\logs
set LOG_FILE=%LOG_DIR%\daily_reset_%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%.log

REM Create log directory if it doesn't exist
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

REM Change to script directory
cd /d "%SCRIPT_DIR%"

REM Activate virtual environment if it exists
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

REM Add timestamp to log
echo === Daily Reset Job Started: %date% %time% === >> "%LOG_FILE%"

REM Run the reset script and capture output
python reset_inactive_accounts.py --all-projects >> "%LOG_FILE%" 2>&1

REM Check exit status
if %errorlevel% equ 0 (
    echo === Daily Reset Job Completed Successfully: %date% %time% === >> "%LOG_FILE%"
    exit /b 0
) else (
    echo === Daily Reset Job Failed: %date% %time% === >> "%LOG_FILE%"
    exit /b 1
)