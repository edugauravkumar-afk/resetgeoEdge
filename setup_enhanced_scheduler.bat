@echo off
REM Windows Scheduler Setup for Enhanced GeoEdge Account Monitoring
REM Run this as Administrator to set up the enhanced daily reset

echo ========================================
echo Setting up Enhanced GeoEdge Scheduler
echo ========================================

REM Check if running as admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: This script must be run as Administrator!
    echo Right-click and select "Run as administrator"
    pause
    exit /b 1
)

REM Set project path (UPDATE THIS PATH TO YOUR ACTUAL PROJECT LOCATION)
set PROJECT_PATH=C:\geoedge-country-projects
set TASK_NAME=GeoEdgeEnhancedReset

echo Project path: %PROJECT_PATH%
echo Task name: %TASK_NAME%

REM Delete existing task if it exists
echo.
echo Removing existing scheduler task if present...
schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1
schtasks /delete /tn "GeoEdgeReset" /f >nul 2>&1
echo Old tasks removed (if they existed)

REM Create new enhanced task
echo.
echo Creating new enhanced daily reset task...
schtasks /create /tn "%TASK_NAME%" ^
    /tr "%PROJECT_PATH%\enhanced_daily_reset.bat" ^
    /sc daily ^
    /st 02:00 ^
    /ru "SYSTEM" ^
    /f

if errorlevel 1 (
    echo ERROR: Failed to create scheduler task!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Enhanced Scheduler Setup Complete!
echo ========================================
echo Task Name: %TASK_NAME%
echo Schedule: Daily at 2:00 AM
echo Script: %PROJECT_PATH%\enhanced_daily_reset.bat
echo.
echo The enhanced system will now:
echo 1. Monitor for newly inactive accounts
echo 2. Immediately reset their projects to (0,0)
echo 3. Send detailed email reports
echo 4. Handle priority accounts before regular processing
echo.
echo To verify the task was created:
echo   schtasks /query /tn "%TASK_NAME%"
echo.
echo To run the task immediately for testing:
echo   schtasks /run /tn "%TASK_NAME%"
echo.

pause