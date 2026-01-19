@echo off
REM Enhanced Daily Reset with Priority Account Monitoring
REM This script handles newly inactive accounts with immediate project reset

echo ========================================
echo GeoEdge Enhanced Daily Reset Starting
echo Time: %date% %time%
echo ========================================

cd /d "C:\geoedge-country-projects"

REM Step 1: Run enhanced monitoring system (includes priority reset)
echo.
echo [%time%] Running enhanced account monitoring and priority reset...
python enhanced_monitoring_system.py

REM Check if enhanced monitoring succeeded
if errorlevel 1 (
    echo [%time%] WARNING: Enhanced monitoring failed, falling back to standard reset
    goto standard_reset
)

echo [%time%] Enhanced monitoring completed successfully
goto email_check

:standard_reset
echo.
echo [%time%] Running standard reset as fallback...
python reset_inactive_accounts.py accounts.txt
if errorlevel 1 (
    echo [%time%] ERROR: Standard reset also failed!
    goto error_exit
)

:email_check
echo.
echo [%time%] Checking email delivery...
REM Email should be sent by the enhanced system or standard reset

:success_exit
echo.
echo ========================================
echo GeoEdge Enhanced Daily Reset Completed
echo Time: %date% %time%
echo Status: SUCCESS
echo ========================================
exit /b 0

:error_exit
echo.
echo ========================================
echo GeoEdge Enhanced Daily Reset FAILED
echo Time: %date% %time%
echo Status: ERROR - Check logs above
echo ========================================
exit /b 1