# GeoEdge Auto Mode Monitoring System - Windows Deployment Guide

## Overview
This system monitors **only** accounts that have Auto Mode configuration (1,72) and automatically resets their projects to Manual Mode (0,0) when those specific accounts become inactive.

## System Components

### Core Files
- `account_status_monitor.py` - Monitors Auto Mode accounts for inactivity
- `daily_monitor_service.py` - Self-executing daily monitoring service
- `email_reporter.py` - Professional email reporting with Auto Mode focus
- `start_monitor.py` - Simple startup script
- `test_auto_mode_system.py` - Comprehensive testing suite

### Supporting Files
- `geoedge_projects/client.py` - Database client
- `.env` - Environment configuration
- `requirements.txt` - Python dependencies

## Windows Deployment Steps

### Step 1: Prepare Your Environment
```bash
# 1. Open PowerShell as Administrator
# 2. Navigate to your projects directory
cd C:\path\to\your\projects

# 3. Clone/copy the project files
# (Copy all files from this repository to your Windows machine)
```

### Step 2: Python Environment Setup
```bash
# 1. Ensure Python 3.8+ is installed
python --version

# 2. Create virtual environment
python -m venv geoedge_auto_monitor

# 3. Activate virtual environment
geoedge_auto_monitor\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt
```

### Step 3: Database Configuration
Create/update `.env` file:
```
# Database Configuration
DB_HOST=your_mysql_host
DB_USER=your_mysql_username  
DB_PASSWORD=your_mysql_password
DB_NAME=TRC
DB_PORT=3306

# Email Configuration
SMTP_HOST=your_smtp_server
SMTP_PORT=587
SMTP_USER=your_email@domain.com
SMTP_PASSWORD=your_email_password
FROM_EMAIL=your_email@domain.com
RECIPIENTS=recipient1@domain.com,recipient2@domain.com
CC_RECIPIENTS=cc1@domain.com,cc2@domain.com

# Optional: SSL Configuration
SMTP_USE_TLS=true
SMTP_USE_SSL=false
```

### Step 4: Test the System
```bash
# Run comprehensive tests
python test_auto_mode_system.py

# Expected output:
# ✅ Auto Mode accounts found: [X number]
# ⚠️  Currently inactive: [X number] 
# 🔧 Projects reset today: [X number]
# 🛠️  Daily service: ✅ Working
# 📧 Email system: ✅ Working
# 🎉 AUTO MODE MONITORING SYSTEM IS READY!
```

### Step 5: Configure Windows Service (Option 1 - Recommended)

#### Install as Windows Service using NSSM
```bash
# 1. Download NSSM (Non-Sucking Service Manager)
# Download from: https://nssm.cc/download

# 2. Extract NSSM and add to PATH

# 3. Create the service
nssm install GeoEdgeAutoMonitor

# 4. Configure service in NSSM GUI:
#    Path: C:\path\to\your\projects\geoedge_auto_monitor\Scripts\python.exe
#    Startup directory: C:\path\to\your\projects
#    Arguments: start_monitor.py

# 5. Set service to restart on failure
nssm set GeoEdgeAutoMonitor AppExit Default Restart
nssm set GeoEdgeAutoMonitor AppRestartDelay 30000

# 6. Start the service
nssm start GeoEdgeAutoMonitor
```

### Step 6: Configure Windows Task Scheduler (Option 2 - Alternative)

#### Create Scheduled Task
1. Open Task Scheduler
2. Create Basic Task
3. Configure:
   - **Name**: GeoEdge Auto Mode Monitor
   - **Description**: Monitor Auto Mode accounts and reset projects when accounts become inactive
   - **Trigger**: Daily at 9:00 AM
   - **Action**: Start a program
   - **Program**: `C:\path\to\your\projects\geoedge_auto_monitor\Scripts\python.exe`
   - **Arguments**: `start_monitor.py`
   - **Start in**: `C:\path\to\your\projects`

#### Advanced Settings
- **Run whether user is logged on or not**: ✅
- **Run with highest privileges**: ✅
- **If task fails, restart every**: 30 minutes
- **Attempt restart up to**: 3 times

### Step 7: Configure Startup Script (Option 3 - Boot Startup)

Create `startup_auto_monitor.bat`:
```batch
@echo off
echo Starting GeoEdge Auto Mode Monitor...
cd /d "C:\path\to\your\projects"
call geoedge_auto_monitor\Scripts\activate
python start_monitor.py
pause
```

Add to Windows Startup folder:
- Press `Win + R`, type `shell:startup`
- Copy the batch file to the startup folder

## System Behavior

### What the System Does
1. **Daily at 9:00 AM**: Automatically runs monitoring check
2. **Monitors Only Auto Mode Accounts**: Finds accounts with configuration (1,72)
3. **Detects Inactive Accounts**: Identifies Auto Mode accounts that became inactive in last 24 hours
4. **Resets Projects Automatically**: Updates sp_campaigns from (1,72) to (0,0) for inactive accounts
5. **Sends Professional Reports**: Emails detailed reports with Auto Mode focus

### Email Reports Include
- **Auto Mode Accounts**: Total number of accounts being monitored
- **Became Inactive**: Number that became inactive in last 24 hours
- **Projects Reset**: Actual number of projects reset from (1,72) to (0,0)
- **Detailed Account List**: Shows each account reset with project counts
- **CSV Export**: Complete data export for record keeping

### Database Updates Performed
```sql
-- For each project under inactive Auto Mode accounts:
UPDATE sp_campaigns 
SET auto_scan = 0, scans_per_day = 0 
WHERE pub_id = [inactive_account_id] 
  AND auto_scan = 1 
  AND scans_per_day = 72
```

## Monitoring and Logs

### Log Files Location
- **Service logs**: Check Windows Event Viewer > Applications and Services Logs
- **Application logs**: In project directory (if file logging enabled)

### Log Levels
- **INFO**: Normal operation, accounts found, projects reset
- **WARNING**: Unusual conditions, no Auto Mode accounts found
- **ERROR**: Database connection issues, email failures

### Monitoring Commands
```bash
# Check if service is running (NSSM)
nssm status GeoEdgeAutoMonitor

# Check last execution (Task Scheduler)
# Open Task Scheduler > Task History

# Manual test run
python test_auto_mode_system.py
```

## Troubleshooting

### Common Issues

#### 1. Database Connection Fails
- Check `.env` file configuration
- Verify network connectivity to MySQL server
- Test credentials: `python -c "from geoedge_projects.client import GeoEdgeClient; GeoEdgeClient()"`

#### 2. Email Not Sending
- Verify SMTP settings in `.env`
- Check firewall/antivirus blocking SMTP ports
- Test email: `python test_email.py`

#### 3. Service Won't Start
- Check Python path in service configuration
- Verify virtual environment activation
- Check Windows Event Viewer for error details

#### 4. No Auto Mode Accounts Found
- Check database query in `get_active_auto_scan_accounts()`
- Verify sp_campaigns table has accounts with auto_scan=1 and scans_per_day=72
- Run: `python -c "from account_status_monitor import AccountStatusMonitor; print(len(AccountStatusMonitor().get_active_auto_scan_accounts()))"`

### Manual Testing Commands
```bash
# Test database connection
python -c "from geoedge_projects.client import GeoEdgeClient; print('DB OK')"

# Test Auto Mode account detection  
python -c "from account_status_monitor import AccountStatusMonitor; print(f'Auto Mode accounts: {len(AccountStatusMonitor().get_active_auto_scan_accounts())}')"

# Test email system
python test_email.py

# Full system test
python test_auto_mode_system.py
```

## Security Notes

1. **Database Access**: Ensure database user has minimal required permissions (SELECT, UPDATE on specific tables)
2. **Email Credentials**: Store securely in `.env` file with proper file permissions
3. **Service Account**: Run Windows service with appropriate service account, not administrator
4. **Network Security**: Ensure proper firewall rules for database and SMTP access

## Maintenance

### Regular Maintenance Tasks
1. **Weekly**: Check email reports for unusual patterns
2. **Monthly**: Review log files for errors or warnings
3. **Quarterly**: Update Python dependencies: `pip install -r requirements.txt --upgrade`
4. **As Needed**: Update database credentials if changed

### Backup Considerations
- Backup `.env` file (securely)
- Keep copy of database schema for reference
- Export Auto Mode account list periodically for reference

## Success Indicators

### System is Working Correctly When:
- ✅ Daily emails arrive at 9:00 AM with "Auto Mode Monitor" subject
- ✅ Email shows correct count of "Auto Mode Accounts" being monitored  
- ✅ When accounts become inactive, they appear in "Became Inactive" section
- ✅ Projects are actually reset in database (verify with SQL queries)
- ✅ CSV exports contain accurate data for record keeping

### Contact & Support
- Check project documentation for updates
- Review database query logs for optimization opportunities
- Monitor email delivery rates and adjust SMTP settings as needed

---

**Ready to Deploy**: Once tests pass, the system will automatically monitor your Auto Mode accounts and keep your scanning resources optimized by disabling scanning for inactive accounts.