@echo off
REM Windows Task Scheduler setup for GeoEdge Daily Reset
REM This script creates a scheduled task to run daily at 2:00 AM

echo Creating scheduled task GeoEdge_Daily_Reset...

REM Delete existing task if it exists (ignore errors)
schtasks /delete /tn "GeoEdge_Daily_Reset" /f >nul 2>&1

REM Create the scheduled task
schtasks /create ^
    /tn "GeoEdge_Daily_Reset" ^
    /tr "C:\AF\geoedge-tools\resetgeoEdge\update_and_run.bat" ^
    /sc daily ^
    /st 02:00 ^
    /sd %date% ^
    /rl HIGHEST ^
    /ru "%USERNAME%" ^
    /rp ^
    /f

if %ERRORLEVEL% equ 0 (
    echo.
    echo ✅ SUCCESS: The scheduled task "GeoEdge_Daily_Reset" has successfully been created.
    echo.
    echo 🎯 GeoEdge Reset will run daily at 02:00 AM
    echo 📁 Location: C:\AF\geoedge-tools\resetgeoEdge\
    echo 📋 Task will auto-update code and reset inactive accounts
    echo.
    echo 🔧 Management Commands:
    echo View task: schtasks /query /tn "GeoEdge_Daily_Reset" /v
    echo Enable task: schtasks /change /tn "GeoEdge_Daily_Reset" /enable
    echo Disable task: schtasks /change /tn "GeoEdge_Daily_Reset" /disable
    echo Delete task: schtasks /delete /tn "GeoEdge_Daily_Reset" /f
    echo Run now: schtasks /run /tn "GeoEdge_Daily_Reset"
    echo.
) else (
    echo ❌ ERROR: Failed to create scheduled task
    echo Please run this script as Administrator
)

pause