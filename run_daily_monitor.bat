@echo off
REM GeoEdge Daily Monitor - Windows Batch Script
REM This script runs the daily inactive account monitor

REM Set script directory
cd /d "%~dp0"

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Check if virtual environment activated successfully
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    echo Please ensure .venv\Scripts\activate.bat exists
    pause
    exit /b 1
)

REM Create logs directory if it doesn't exist
if not exist "logs" mkdir logs

REM Set log file with current date
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "YY=%dt:~2,2%" & set "YYYY=%dt:~0,4%" & set "MM=%dt:~4,2%" & set "DD=%dt:~6,2%"
set "datestamp=%YYYY%%MM%%DD%"
set "logfile=logs\daily_monitor_%datestamp%.log"

REM Print startup info
echo ================================================== >> "%logfile%" 2>&1
echo GeoEdge Daily Monitor - Windows Execution >> "%logfile%" 2>&1
echo Start Time: %date% %time% >> "%logfile%" 2>&1
echo ================================================== >> "%logfile%" 2>&1

REM Run the daily monitor
echo Running GeoEdge Daily Monitor...
echo Running GeoEdge Daily Monitor... >> "%logfile%" 2>&1
python daily_inactive_monitor.py >> "%logfile%" 2>&1

REM Check exit code
if errorlevel 1 (
    echo ERROR: Daily monitor failed with exit code %errorlevel% >> "%logfile%" 2>&1
    echo ERROR: Daily monitor execution failed
    pause
    exit /b %errorlevel%
) else (
    echo SUCCESS: Daily monitor completed successfully >> "%logfile%" 2>&1
    echo SUCCESS: Daily monitor completed - check %logfile%
)

REM Deactivate virtual environment
deactivate

echo Daily monitoring completed at %date% %time%
exit /b 0