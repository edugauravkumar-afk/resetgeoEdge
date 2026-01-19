# Windows Daily GeoEdge Reset Scheduler Setup Guide

## For Windows Systems

### Option 1: Windows Task Scheduler (Recommended)

#### Setup Windows Task Scheduler:

1. **Open Task Scheduler:**
   - Press `Win + R`, type `taskschd.msc`, press Enter
   - Or search "Task Scheduler" in Start Menu

2. **Create Basic Task:**
   - Click "Create Basic Task" in Actions panel
   - Name: "GeoEdge Daily Reset"
   - Description: "Reset inactive account projects to manual mode daily"

3. **Set Trigger:**
   - When: "Daily"
   - Start: Choose start date
   - Time: `02:00:00` (2:00 AM)
   - Recur every: `1 days`

4. **Set Action:**
   - Action: "Start a program"
   - Program/script: `C:\path\to\geoedge-country-projects\daily_reset.bat`
   - Start in: `C:\path\to\geoedge-country-projects`

5. **Update Paths:**
   - Edit `daily_reset.bat` and update `SCRIPT_DIR` to your actual path
   - Example: `set SCRIPT_DIR=C:\Users\YourName\Desktop\geoedge-country-projects`

#### Alternative: PowerShell Script
- Use `daily_reset.ps1` instead
- Program/script: `powershell.exe`
- Arguments: `-ExecutionPolicy Bypass -File "C:\path\to\geoedge-country-projects\daily_reset.ps1"`

---

### Option 2: Python Scheduler Service

#### Install Schedule Package:
```cmd
pip install schedule pywin32
```

#### Run as Windows Service:
```cmd
# Install as Windows service (run as Administrator)
python -m pip install pywin32
python daily_scheduler.py install

# Start the service
python daily_scheduler.py start

# Stop the service
python daily_scheduler.py stop

# Remove the service
python daily_scheduler.py remove
```

#### Or Run Manually:
```cmd
# Start scheduler (keep window open)
python daily_scheduler.py

# Test run immediately
python daily_scheduler.py --test
```

---

## Git Setup on Windows Nginx Server

### 1. Clone Repository:
```cmd
# Navigate to your desired directory
cd C:\nginx\html\geoedge-tools
# or wherever you want to place the project

# Clone the repository
git clone https://github.com/edugauravkumar-afk/resetgeoEdge.git
cd resetgeoEdge
```

### 2. Setup Python Environment:
```cmd
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.venv\Scripts\activate.bat

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment:
```cmd
# Copy environment template
copy .env.example .env

# Edit .env with your credentials (use notepad or any editor)
notepad .env
```

### 4. Set Up Scheduler:
```cmd
# Update paths in batch file
notepad daily_reset.bat
# Change SCRIPT_DIR to your actual path

# Test the script
daily_reset.bat

# Set up Windows Task Scheduler (follow steps above)
```

### 5. Auto-Update from Git:
Create `update_and_run.bat`:
```batch
@echo off
cd C:\nginx\html\geoedge-tools\resetgeoEdge
git pull origin main
call daily_reset.bat
```

---

## Monitoring on Windows

### View Logs:
```cmd
# Navigate to logs directory
cd C:\path\to\geoedge-country-projects\logs

# View latest log file
type daily_reset_*.log | more

# View in real-time (PowerShell)
Get-Content daily_reset_*.log -Wait
```

### Check Task Scheduler:
1. Open Task Scheduler
2. Look for "GeoEdge Daily Reset" task
3. Check "Last Run Result" and "Last Run Time"

### Service Status (if using Python service):
```cmd
# Check service status
sc query "GeoEdge Reset Scheduler"

# View service logs
type logs\scheduler_*.log
```

---

## Example Windows Paths:

Update these paths in your batch files:
```batch
REM Example paths - update to match your system
set SCRIPT_DIR=C:\Users\%USERNAME%\Desktop\geoedge-country-projects
set SCRIPT_DIR=C:\nginx\html\geoedge-tools\resetgeoEdge
set SCRIPT_DIR=D:\projects\geoedge-reset
```

---

## Troubleshooting Windows

- **Permission Issues**: Run Command Prompt as Administrator
- **PowerShell Execution Policy**: Run `Set-ExecutionPolicy RemoteSigned`
- **Python Not Found**: Add Python to PATH or use full path
- **Virtual Environment Issues**: Use `.venv\Scripts\activate.bat` not `.venv\bin\activate`