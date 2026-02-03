@echo off
echo Creating scheduled task GeoEdge_Daily_Monitor...

schtasks /create /tn "GeoEdge_Daily_Monitor" /tr "cmd /c cd /d C:\AF\geoedge-tools && C:\AF\geoedge-tools\.venv\Scripts\python.exe account_status_monitor_fixed.py >> daily_monitor.log 2>&1" /sc daily /st 09:00 /f

if %errorlevel% equ 0 (
    echo.
    echo Success Task created.
    echo GeoEdge Daily Monitor will run daily at 09:00 AM
    echo.
    echo View task: schtasks /query /tn "GeoEdge_Daily_Monitor" /v
    echo Delete task: schtasks /delete /tn "GeoEdge_Daily_Monitor" /f
    echo Enable task: schtasks /change /tn "GeoEdge_Daily_Monitor" /enable
    echo Disable task: schtasks /change /tn "GeoEdge_Daily_Monitor" /disable
    echo Run now: schtasks /run /tn "GeoEdge_Daily_Monitor"
) else (
    echo Failed to create task. Run as Administrator.
)

echo.
pause
