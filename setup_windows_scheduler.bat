@echo off
REM Windows Task Scheduler Setup for GeoEdge Daily Monitor
REM This script creates a Windows Task Scheduler entry to run the daily monitor

echo ================================================
echo   GeoEdge Daily Monitor - Windows Scheduler Setup
echo ================================================

REM Get current directory
set SCRIPT_DIR=%~dp0
set BATCH_FILE=%SCRIPT_DIR%run_daily_monitor.bat

REM Check if batch file exists
if not exist "%BATCH_FILE%" (
    echo ERROR: Batch file not found: %BATCH_FILE%
    echo Please ensure run_daily_monitor.bat exists in the same directory
    pause
    exit /b 1
)

echo Current Directory: %SCRIPT_DIR%
echo Batch Script: %BATCH_FILE%
echo.

REM Check if virtual environment exists
if not exist "%SCRIPT_DIR%.venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found
    echo Please run: python -m venv .venv
    echo Then: .venv\Scripts\activate.bat
    echo Then: pip install -r requirements.txt
    pause
    exit /b 1
)

REM Check if daily monitor script exists
if not exist "%SCRIPT_DIR%daily_inactive_monitor.py" (
    echo ERROR: Daily monitor script not found
    echo Please ensure daily_inactive_monitor.py exists
    pause
    exit /b 1
)

echo ✅ All required files found
echo.

REM Create logs directory
if not exist "%SCRIPT_DIR%logs" mkdir "%SCRIPT_DIR%logs"

echo 📅 Setting up Windows Task Scheduler...
echo.

REM Create the scheduled task
schtasks /create /tn "GeoEdge Daily Monitor" ^
    /tr "\"%BATCH_FILE%\"" ^
    /sc daily ^
    /st 09:00 ^
    /ru "SYSTEM" ^
    /f

if errorlevel 1 (
    echo.
    echo ❌ Failed to create scheduled task
    echo.
    echo Manual Setup Instructions:
    echo 1. Open Task Scheduler (taskschd.msc)
    echo 2. Click "Create Basic Task"
    echo 3. Name: "GeoEdge Daily Monitor"
    echo 4. Trigger: Daily
    echo 5. Time: 09:00 AM (or preferred time)
    echo 6. Action: Start a program
    echo 7. Program: %BATCH_FILE%
    echo.
    pause
    exit /b 1
)

echo ✅ Scheduled task created successfully!
echo.
echo 📋 Task Details:
echo    Task Name: "GeoEdge Daily Monitor"
echo    Schedule: Daily at 9:00 AM
echo    Script: %BATCH_FILE%
echo    User: SYSTEM
echo.

REM Show the created task
echo 📊 Task Information:
schtasks /query /tn "GeoEdge Daily Monitor" /fo LIST

echo.
echo 🛠️  Task Management Commands:
echo    View task:    schtasks /query /tn "GeoEdge Daily Monitor"
echo    Run now:      schtasks /run /tn "GeoEdge Daily Monitor"
echo    Disable:      schtasks /change /tn "GeoEdge Daily Monitor" /disable
echo    Enable:       schtasks /change /tn "GeoEdge Daily Monitor" /enable
echo    Delete:       schtasks /delete /tn "GeoEdge Daily Monitor" /f
echo.

REM Offer to test run
set /p TESTRUN="🧪 Would you like to test run the monitor now? (y/n): "
if /i "%TESTRUN%"=="y" (
    echo.
    echo 🔄 Running test...
    call "%BATCH_FILE%"
    echo.
    echo ✅ Test completed. Check logs directory for output.
) else (
    echo.
    echo ℹ️  You can test manually later with: "%BATCH_FILE%"
)

echo.
echo 📊 Setup Complete!
echo    Logs will be stored in: %SCRIPT_DIR%logs\
echo    State file: %SCRIPT_DIR%daily_monitor_state.json
echo    Daily execution: 9:00 AM (modify with Task Scheduler if needed)
echo.

pause