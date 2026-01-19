# 🚀 WINDOWS DEPLOYMENT GUIDE - Enhanced Account Monitoring System

## 📋 Complete Step-by-Step Deployment Instructions

### Prerequisites
- Windows machine with Python 3.7+ installed
- Git installed for code deployment
- Administrator access for scheduler setup
- Database and email credentials configured

---

## 🔄 STEP 1: Git Deployment

### Push All Files to Git
```bash
# From your development machine, push all enhanced files
git add .
git commit -m "Enhanced account monitoring system with priority reset"
git push origin main
```

### Files to be deployed:
✅ `account_status_monitor.py` - Baseline comparison monitoring  
✅ `analyze_deactivation.py` - Investigation and analysis tools  
✅ `enhanced_monitoring_system.py` - Main integration system  
✅ `priority_reset_handler.py` - Priority account reset handler  
✅ `enhanced_daily_reset.bat` - Windows batch script  
✅ `setup_enhanced_scheduler.bat` - Scheduler setup script  
✅ `deactivation_queries.sql` - Manual investigation queries  
✅ `ENHANCED_ACCOUNT_MONITORING_README.md` - Complete documentation  

---

## 🖥️ STEP 2: Windows Machine Setup

### 1. Clone/Pull Latest Code
```cmd
cd C:\
git clone https://github.com/your-repo/geoedge-country-projects.git
# OR if already exists:
cd C:\geoedge-country-projects
git pull origin main
```

### 2. Verify Python Environment
```cmd
cd C:\geoedge-country-projects
python --version
pip install -r requirements.txt
```

### 3. Set Environment Variables
**Create/Update `.env` file with:**
```env
# Database Configuration
MYSQL_HOST=your-database-host
MYSQL_PORT=3306
MYSQL_USER=your-db-user
MYSQL_PASSWORD=your-db-password
MYSQL_DB=TRC

# GeoEdge API
GEOEDGE_API_BASE=https://api.geoedge.com
GEOEDGE_API_KEY=your-api-key

# Email Configuration  
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=your-sender@gmail.com
TO_EMAILS=recipient1@company.com,recipient2@company.com
```

---

## ⚙️ STEP 3: Windows Scheduler Configuration

### 1. Run Scheduler Setup (AS ADMINISTRATOR)
```cmd
# Right-click Command Prompt → "Run as administrator"
cd C:\geoedge-country-projects
.\setup_enhanced_scheduler.bat
```

### Expected Output:
```
========================================
Enhanced Scheduler Setup Complete!
========================================
Task Name: GeoEdgeEnhancedReset
Schedule: Daily at 2:00 AM
Script: C:\geoedge-country-projects\enhanced_daily_reset.bat
```

### 2. Verify Scheduler Task
```cmd
schtasks /query /tn "GeoEdgeEnhancedReset"
```

---

## 🧪 STEP 4: Testing

### 1. Test Account Monitoring
```cmd
cd C:\geoedge-country-projects
python account_status_monitor.py
```
**Expected**: Creates initial baseline with ~967,922 accounts

### 2. Test Enhanced System
```cmd
python enhanced_monitoring_system.py
```
**Expected**: Runs monitoring, reports "No newly inactive accounts found"

### 3. Test Email System
```cmd
python test_email.py
```
**Expected**: Sends test email with enhanced formatting

### 4. Test Priority Reset (Dry Run)
```cmd
python priority_reset_handler.py
```
**Expected**: Shows priority monitoring without actual changes

### 5. Test Full Scheduler
```cmd
# Run the scheduled task immediately
schtasks /run /tn "GeoEdgeEnhancedReset"
```

---

## 📧 STEP 5: Email Configuration Verification

### Gmail Setup (if using Gmail):
1. Enable 2-Factor Authentication
2. Generate App Password: Google Account → Security → App passwords
3. Use App Password (not regular password) in `SMTP_PASSWORD`

### Email Template Test:
The enhanced emails now include:
- ✅ **Priority Account Alerts**: Highlighted newly inactive accounts
- ✅ **Scan Configuration Tables**: Auto Scan and Scans/Day columns  
- ✅ **CSV Export Enhanced**: Includes scan settings data
- ✅ **Color Coding**: Red for priority, green for success

---

## 🔍 STEP 6: Monitoring & Verification

### Daily Verification Checklist:
- [ ] Email report received at expected time (after 2:00 AM)
- [ ] Subject line shows date and account count
- [ ] CSV attachment includes scan configuration columns
- [ ] "No newly inactive accounts found" (most days) 
- [ ] If priority accounts found, immediate reset confirmation

### Weekly Checks:
- [ ] Check baseline file date: Check if `/tmp/account_status_baseline.json` is updated
- [ ] Review Windows Event Logs for scheduler errors
- [ ] Verify database connectivity with `python analyze_deactivation.py`

### Monthly Audits:
- [ ] Run manual investigation queries from `deactivation_queries.sql`
- [ ] Check for accounts missed by monitoring system
- [ ] Review email deliverability and formatting

---

## 🚨 TROUBLESHOOTING

### Common Issues & Solutions:

#### 1. "No newly inactive accounts found" but you expect some:
```cmd
# Check baseline age and compare manually
python analyze_deactivation.py
```

#### 2. Email not sending:
```cmd
# Test email configuration
python test_email.py
# Check environment variables
echo %SMTP_USER%
echo %FROM_EMAIL%
```

#### 3. Database connection issues:
```cmd
# Test database connection
python -c "from account_status_monitor import AccountStatusMonitor; m = AccountStatusMonitor(); print('DB OK')"
```

#### 4. Scheduler task not running:
```cmd
# Check task status
schtasks /query /tn "GeoEdgeEnhancedReset" /v
# Check Windows Event Viewer → Task Scheduler logs
```

#### 5. Priority reset not working:
```cmd
# Check GeoEdge API connectivity
python -c "from geoedge_projects.client import GeoEdgeClient; c = GeoEdgeClient(); print('API OK')"
```

---

## 📊 Success Metrics

### Immediate Success Indicators:
- ✅ Scheduler task created and running daily
- ✅ Email reports received with enhanced formatting
- ✅ Baseline file updates daily
- ✅ No errors in Windows Event Logs

### Long-term Success Indicators:
- ✅ When accounts become inactive, immediate project reset confirmation in email
- ✅ Zero continued scanning charges from inactive accounts
- ✅ Enhanced email reports show scan configuration details
- ✅ CSV exports include auto_scan and scans_per_day data

### Example Success Email:
```
Subject: ✅ GeoEdge Daily Reset Report - 2026-01-20 - 0 Priority | 125 Reset

🚨 PRIORITY ACCOUNT ALERTS: 0 newly inactive accounts found

📊 ACCOUNT RESET SUMMARY:
Total Accounts Processed: 125
Projects Reset to Manual Mode: 2,847

📋 SCAN CONFIGURATION DETAILS:
Account ID | Name                | Auto Scan | Scans/Day | Projects | Status
-----------|--------------------|-----------|-----------|-----------|---------
1234567    | example-account    |     0     |     0     |    42    | RESET

✅ All inactive accounts have projects set to manual mode (0,0)
```

---

## 🎯 FINAL VERIFICATION

### Complete System Test:
1. ✅ All files deployed to Windows machine
2. ✅ Environment variables configured  
3. ✅ Scheduler task created and verified
4. ✅ Email system tested and working
5. ✅ Database connectivity confirmed
6. ✅ Baseline monitoring operational
7. ✅ Priority reset system ready

### System is Ready! 🚀

The enhanced monitoring system will now:
- **Monitor** account status changes continuously
- **Detect** newly inactive accounts within hours  
- **Reset** ALL projects under inactive accounts to (0,0) immediately
- **Report** priority actions and scan configurations in detailed emails
- **Prevent** wasted scanning costs from inactive accounts

Your GeoEdge account monitoring is now **fully automated** and **proactive**! 🎉