# Windows Deployment Guide - Daily GeoEdge Monitor

## 📥 Step 1: Pull Code from Git on Windows

### Option A: Using Git Bash or PowerShell
```bash
# Navigate to your projects directory
cd C:\Users\YourUsername\Documents\Projects

# Clone the repository (first time)
git clone https://github.com/edugauravkumar-afk/resetgeoEdge.git
cd resetgeoEdge

# OR if already cloned, just pull latest changes
cd C:\Users\YourUsername\Documents\Projects\resetgeoEdge
git pull origin main
```

### Option B: Using GitHub Desktop
1. Download and install GitHub Desktop
2. File → Clone Repository
3. Enter: `edugauravkumar-afk/resetgeoEdge`
4. Choose local path (e.g., `C:\Users\YourUsername\Documents\Projects`)
5. Click "Clone"

**To Update Later:**
- Open GitHub Desktop
- Click "Fetch origin" → "Pull origin"

---

## 🔧 Step 2: Install Python Environment on Windows

### 2.1 Install Python (if not already)
```bash
# Download from https://www.python.org/downloads/
# During installation, CHECK "Add Python to PATH"
```

### 2.2 Create Virtual Environment
```bash
# Open Command Prompt as Administrator
cd C:\Users\YourUsername\Documents\Projects\resetgeoEdge

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2.3 Configure Environment Variables
Create `.env` file in project root:
```
DB_HOST=your_database_host
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_NAME=TRC

GEOEDGE_API_KEY=your_api_key
GEOEDGE_API_BASE=https://api.geoedge.com/rest/analytics/v3

SMTP_SERVER=ildcsmtp.office.taboola.com
SMTP_PORT=25
SENDER_EMAIL=GeoEdgeConfigChangeAlerts@taboola.com
RECIPIENT_EMAILS=gaurav.k@taboola.com,other.email@taboola.com
```

---

## ⏰ Step 3: Setup Windows Task Scheduler

### 🎯 FILE TO RUN DAILY: `daily_inactive_monitor.py`

This is the main file that will run daily. It will:
- Check all active accounts for inactivity
- Update projects to Manual Mode if needed
- Send email reports

### Method 1: Automated Setup (Recommended)

**Run the provided batch file:**
```bash
# Right-click and "Run as Administrator"
setup_windows_scheduler.bat
```

This will automatically:
- Set schedule to run daily at 9:00 AM
- Configure proper paths
- Set up logging

### Method 2: Manual Setup

#### Step 2.1: Create Execution Batch File

The project already has `run_daily_monitor.bat`:
```batch
@echo off
REM GeoEdge Daily Monitor - Windows Execution Script

REM Navigate to project directory
cd /d C:\Users\YourUsername\Documents\Projects\resetgeoEdge

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Run the daily monitor
python daily_inactive_monitor.py

REM Log completion
echo Daily monitor completed at %date% %time% >> monitor_runs.log

pause
```

**Important:** Edit the path in line 5 to match your actual project location!

#### Step 2.2: Open Task Scheduler
1. Press `Win + R`
2. Type `taskschd.msc`
3. Press Enter

#### Step 2.3: Create New Task
1. Click **"Create Basic Task"** in right panel
2. **Name**: `GeoEdge Daily Monitor`
3. **Description**: `Daily monitoring for inactive GeoEdge accounts`
4. Click **Next**

#### Step 2.4: Set Trigger (When to Run)
1. Select **"Daily"**
2. Click **Next**
3. **Start date**: Today's date
4. **Time**: `09:00:00` (9:00 AM)
5. **Recur every**: `1` days
6. Click **Next**

#### Step 2.5: Set Action (What to Run)
1. Select **"Start a program"**
2. Click **Next**
3. **Program/script**: Browse to `run_daily_monitor.bat`
   - Full path example: `C:\Users\YourUsername\Documents\Projects\resetgeoEdge\run_daily_monitor.bat`
4. **Start in**: Enter project directory
   - Example: `C:\Users\YourUsername\Documents\Projects\resetgeoEdge`
5. Click **Next**

#### Step 2.6: Advanced Settings
1. Click **Finish**
2. Right-click the created task → **Properties**
3. **General tab**:
   - Check "Run whether user is logged on or not"
   - Check "Run with highest privileges"
4. **Conditions tab**:
   - Uncheck "Start the task only if the computer is on AC power"
   - Check "Wake the computer to run this task"
5. **Settings tab**:
   - Check "Run task as soon as possible after a scheduled start is missed"
   - Check "If the task fails, restart every: 10 minutes, 3 times"
6. Click **OK**

---

## 🧪 Step 4: Test the Schedule

### Test Immediately
1. Open Task Scheduler
2. Find "GeoEdge Daily Monitor"
3. Right-click → **Run**
4. Check email for report
5. Check log file: `daily_monitor_YYYYMMDD.log`

### Expected Result
Within 2-3 minutes:
- ✅ Email arrives in your inbox
- ✅ Log file created in project directory
- ✅ State file updated: `daily_monitor_state.json`

---

## 📊 What Happens When Scheduler Runs?

### Daily at 9:00 AM:
```
1. Task Scheduler wakes up
   ↓
2. Runs: run_daily_monitor.bat
   ↓
3. Batch file activates Python virtual environment
   ↓
4. Executes: daily_inactive_monitor.py
   ↓
5. Script performs:
   - Connects to database
   - Queries all accounts with Auto Mode (1,72)
   - Checks for alerts in last 30 days
   - Identifies newly inactive accounts
   - Updates their projects to Manual Mode (0,0) via API
   - Generates email report
   - Sends email to recipients
   - Saves state for next day
   ↓
6. You receive email report:
   - ⚠️ Alert email (if inactive accounts found)
   - ✅ Success email (if no changes)
```

---

## 📧 Email Reports You'll Receive

### Scenario 1: Inactive Accounts Found
```
Subject: ⚠️ GeoEdge Daily Monitor - X Inactive Accounts - 2026-01-20

Content:
┌─────────────────────────────────────────┐
│ Last 24 Hours Activity                  │
├─────────────────────────────────────────┤
│ ⚠️ Inactive Accounts: X                 │
│ 🔧 Projects Updated: Y → (0,0)          │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ Current System Status                   │
├─────────────────────────────────────────┤
│ 👥 Active Accounts: 3,337 / 3,534       │
│ 📁 Active Projects: 13,399 / 15,420     │
└─────────────────────────────────────────┘

+ Detailed table with account IDs
```

### Scenario 2: No Changes
```
Subject: ✅ GeoEdge Daily Monitor - No Changes - 2026-01-20

Content:
🎉 All Systems Optimal
No inactive accounts detected in the last 24 hours

┌─────────────────────────────────────────┐
│ Last 24 Hours Activity                  │
├─────────────────────────────────────────┤
│ ✅ Inactive Accounts: 0                 │
│ ✅ Projects Updated: 0                  │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ Current System Status                   │
├─────────────────────────────────────────┤
│ 👥 Active Accounts: 3,337 / 3,534       │
│ 📁 Active Projects: 13,399 / 15,420     │
└─────────────────────────────────────────┘
```

---

## 🔍 Monitoring & Troubleshooting

### Check Task Status
```bash
# Open Task Scheduler
# Navigate to: Task Scheduler Library
# Find: GeoEdge Daily Monitor
# Check: Last Run Result (should be 0x0 for success)
```

### View Logs
```bash
# Daily execution logs
cd C:\Users\YourUsername\Documents\Projects\resetgeoEdge
type daily_monitor_20260120.log

# Task execution log
type monitor_runs.log
```

### Check State File
```bash
type daily_monitor_state.json
```

### Common Issues

**Problem**: Task shows "Running" but never completes
- **Solution**: Check Python path in batch file is correct
- **Solution**: Verify virtual environment exists

**Problem**: Email not received
- **Solution**: Check `.env` file has correct SMTP settings
- **Solution**: Verify RECIPIENT_EMAILS is correct
- **Solution**: Check Windows Firewall isn't blocking SMTP

**Problem**: Database connection failed
- **Solution**: Verify database credentials in `.env`
- **Solution**: Check VPN/network connection if database is remote
- **Solution**: Test connection manually: `python test_database.py`

**Problem**: Task didn't run at scheduled time
- **Solution**: Check "Wake the computer to run this task" is enabled
- **Solution**: Ensure computer isn't in sleep/hibernate mode at 9 AM
- **Solution**: Check task hasn't been disabled accidentally

---

## 📅 Changing the Schedule

### To Run at Different Time
1. Open Task Scheduler
2. Right-click task → **Properties**
3. **Triggers** tab → **Edit**
4. Change time (e.g., 08:00:00 for 8 AM)
5. Click **OK**

### To Run Multiple Times Per Day
1. **Triggers** tab → **New**
2. Add additional triggers (e.g., 9 AM and 5 PM)

### To Disable Temporarily
1. Right-click task → **Disable**
2. To resume: Right-click → **Enable**

---

## 🔄 Updating the Code

When new updates are pushed to Git:

```bash
# Open Command Prompt
cd C:\Users\YourUsername\Documents\Projects\resetgeoEdge

# Pull latest changes
git pull origin main

# Update dependencies (if requirements.txt changed)
.venv\Scripts\activate
pip install -r requirements.txt --upgrade
```

The next scheduled run will use the updated code automatically.

---

## 🎯 Quick Reference

| Item | Value |
|------|-------|
| **Main File** | `daily_inactive_monitor.py` |
| **Batch File** | `run_daily_monitor.bat` |
| **Schedule** | Daily at 9:00 AM |
| **Log File** | `daily_monitor_YYYYMMDD.log` |
| **State File** | `daily_monitor_state.json` |
| **Email Subject** | `⚠️ GeoEdge Daily Monitor - ...` |
| **Accounts Monitored** | 3,337 active accounts |
| **Projects Monitored** | 13,399 active projects |

---

## ✅ Checklist for Windows Setup

- [ ] Pull code from GitHub
- [ ] Install Python with PATH
- [ ] Create virtual environment
- [ ] Install requirements
- [ ] Configure .env file
- [ ] Edit path in run_daily_monitor.bat
- [ ] Run setup_windows_scheduler.bat (or manual setup)
- [ ] Test run the task manually
- [ ] Verify email received
- [ ] Check log files created
- [ ] Confirm task shows in Task Scheduler
- [ ] Document local paths for team reference

---

## 📞 Support

If issues persist:
1. Check log files for error messages
2. Test Python script manually: `python daily_inactive_monitor.py`
3. Review `.env` configuration
4. Verify database connectivity
5. Confirm API key is valid

**All set! Your Windows machine will now automatically monitor GeoEdge accounts daily at 9:00 AM.** 🚀
