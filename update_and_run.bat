@echo off
REM Windows Batch script for daily GeoEdge account reset with auto-update from git

REM Configuration
set SCRIPT_DIR=C:\nginx\html\geoedge-tools\resetgeoEdge
REM Update the above path to match your actual project location

REM Create logs directory
if not exist "%SCRIPT_DIR%\logs" mkdir "%SCRIPT_DIR%\logs"

REM Set log file with timestamp
for /f "tokens=1-3 delims=/ " %%i in ('date /t') do set today=%%k-%%i-%%j
for /f "tokens=1-2 delims=: " %%i in ('time /t') do set now=%%i-%%j
set now=%now: =0%
set LOG_FILE=%SCRIPT_DIR%\logs\daily_reset_%today%_%now%.log

echo Starting daily GeoEdge reset at %date% %time% > "%LOG_FILE%"

REM Change to script directory
cd /d "%SCRIPT_DIR%"

REM Update from git
echo Updating from git repository... >> "%LOG_FILE%"
git pull origin main >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Git pull failed >> "%LOG_FILE%"
    echo Git pull failed at %date% %time%
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment... >> "%LOG_FILE%"
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo ERROR: Virtual environment not found >> "%LOG_FILE%"
    echo Virtual environment not found. Please run setup.bat first.
    pause
    exit /b 1
)

REM Install/update requirements
echo Updating requirements... >> "%LOG_FILE%"
pip install -r requirements.txt >> "%LOG_FILE%" 2>&1

REM Run the reset script
echo Running reset inactive accounts script... >> "%LOG_FILE%"
python reset_inactive_accounts.py >> "%LOG_FILE%" 2>&1

if %ERRORLEVEL% equ 0 (
    echo Daily reset completed successfully at %date% %time% >> "%LOG_FILE%"
    echo Daily reset completed successfully at %date% %time%
    echo Email report will be sent automatically if configured >> "%LOG_FILE%"
) else (
    echo ERROR: Daily reset failed at %date% %time% >> "%LOG_FILE%"
    echo Daily reset failed at %date% %time%
    echo Attempting to send error notification... >> "%LOG_FILE%"
    python -c "
try:
    from email_reporter import GeoEdgeEmailReporter
    import os
    reporter = GeoEdgeEmailReporter()
    reporter.send_daily_reset_report({
        'status': 'error',
        'error_message': 'Daily reset script failed with exit code %ERRORLEVEL%',
        'total_accounts_checked': 0,
        'inactive_accounts': 0, 
        'active_accounts': 0,
        'total_projects_scanned': 0,
        'projects_reset': 0,
        'execution_time': 0
    })
    print('Error notification sent')
except Exception as e:
    print(f'Failed to send error email: {e}')
" >> "%LOG_FILE%" 2>&1
    exit /b 1
)

REM Deactivate virtual environment
deactivate

echo Script execution completed. Check log file: %LOG_FILE%