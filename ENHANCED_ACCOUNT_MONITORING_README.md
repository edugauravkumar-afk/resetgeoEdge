# 🔍 ACCOUNT DEACTIVATION DETECTION & AUTOMATIC RESET SYSTEM

## Overview
This enhanced system monitors for newly inactive accounts and ensures their projects are immediately reset to manual mode (0,0) to prevent continued scanning charges.

## 🚨 Critical Problem Solved
**Issue**: When accounts become inactive, their projects continue scanning automatically, wasting resources and incurring charges.

**Solution**: 
1. **Real-time Detection**: Monitor account status changes and identify newly inactive accounts within hours
2. **Immediate Reset**: Automatically reset ALL projects under newly inactive accounts to (0,0)
3. **Priority Processing**: Handle newly inactive accounts before regular maintenance
4. **Comprehensive Reporting**: Email notifications with detailed scan configuration changes

## 📁 New Files Created

### 1. `account_status_monitor.py`
**Purpose**: Baseline comparison system to detect newly inactive accounts
- Creates snapshots of account statuses
- Compares current state with previous baseline
- Identifies accounts that changed from ACTIVE/LIVE → INACTIVE
- Saves priority account lists for immediate processing

### 2. `analyze_deactivation.py` 
**Purpose**: Investigation tool to understand account deactivation patterns
- Finds accounts deactivated in last 24 hours
- Shows projects under recently inactive accounts
- Provides SQL queries for manual investigation
- Creates baseline files for monitoring

### 3. `enhanced_monitoring_system.py`
**Purpose**: Complete integration system combining monitoring, reset, and reporting
- Runs account status monitoring
- Triggers priority resets for newly inactive accounts
- Sends enhanced email reports with priority account details
- Creates SQL query files for manual troubleshooting

### 4. `priority_reset_handler.py`
**Purpose**: Handles actual project resets for newly inactive accounts
- Integrates with existing `reset_inactive_accounts.py` logic
- Resets ALL projects (not just recent ones) for newly inactive accounts
- Provides detailed success/error reporting
- Works with existing GeoEdge API client

### 5. `deactivation_queries.sql`
**Purpose**: Manual investigation queries for account deactivation analysis
- Find accounts deactivated in last 24 hours
- Count projects under recently inactive accounts
- Check specific account project details
- Status distribution analysis

## 🔄 Integration with Existing System

### Enhanced Main Reset Script
The existing `reset_inactive_accounts.py` now includes:
```python
# Step 1: Detect newly inactive accounts before processing
try:
    from detect_inactive_accounts import enhanced_reset_for_status_changes
    print("🔍 Checking for newly inactive accounts...")
    newly_inactive = enhanced_reset_for_status_changes()
    
    if newly_inactive:
        print(f"🚨 PRIORITY: Found {len(newly_inactive)} newly inactive accounts!")
        print("   These will be processed with ALL their projects")
        # Add to priority processing list
```

### Enhanced Email Reporter
The `email_reporter.py` now includes:
- **Auto Scan Configuration Tables**: Shows which accounts have auto_scan enabled/disabled
- **Scans Per Day Details**: Clear indication of scan frequency settings
- **Priority Account Highlighting**: Special formatting for newly inactive accounts
- **CSV Export Enhanced**: Includes scan configuration data in exports

## 🎯 How It Works

### Daily Workflow:
1. **Baseline Check**: Compare current account statuses with previous day's baseline
2. **Priority Detection**: Identify accounts that became INACTIVE since last run
3. **Immediate Reset**: Reset ALL projects under newly inactive accounts to (0,0)
4. **Regular Processing**: Continue with normal reset logic for other accounts
5. **Enhanced Reporting**: Send email with priority account details and scan configurations
6. **Baseline Update**: Save new baseline for next day's comparison

### Example Detection:
```
🚨 PRIORITY HANDLING: 5 newly inactive accounts
   Account ID    Name                    Old→New      Projects  Campaigns
   1878208       clevercrowads-sc        LIVE→INACTIVE      72        247
   1953730       level-upadsco-sc        LIVE→INACTIVE      46         92
   
🎯 TOTAL PROJECTS NEEDING IMMEDIATE RESET: 118
```

## 📧 Enhanced Email Reports

### New Email Features:
- **Priority Account Section**: Highlights newly inactive accounts requiring immediate attention
- **Scan Configuration Table**: 
  ```
  Account ID | Account Name          | Auto Scan | Scans/Day | Total Projects | Status
  1878208    | clevercrowads-sc      |    0      |     0     |      72       | NEWLY_INACTIVE_PRIORITY
  ```
- **Enhanced CSV Export**: Includes auto_scan and scans_per_day columns
- **Color Coding**: Red highlighting for priority accounts, green for successfully reset accounts

## 🛠️ Deployment Instructions

### 1. File Placement
Copy these files to your Windows machine:
- `account_status_monitor.py`
- `analyze_deactivation.py` 
- `enhanced_monitoring_system.py`
- `priority_reset_handler.py`
- `deactivation_queries.sql`

### 2. Update Windows Scheduler
**Replace your existing scheduled command with:**
```batch
@echo off
cd /d "C:\\path\\to\\your\\project"
python enhanced_monitoring_system.py
if errorlevel 1 (
    echo Priority monitoring failed, running standard reset
    python reset_inactive_accounts.py accounts.txt
)
```

### 3. Scheduler Configuration
```batch
# Delete existing task
schtasks /delete /tn "GeoEdgeReset" /f

# Create new enhanced task
schtasks /create /tn "GeoEdgeEnhancedReset" /tr "C:\\path\\to\\update_and_run.bat" /sc daily /st 02:00 /f
```

### 4. Environment Variables
Ensure these are set:
```
MYSQL_HOST=your-database-host
MYSQL_USER=your-db-user
MYSQL_PASSWORD=your-db-password
MYSQL_DB=TRC
SMTP_SERVER=your-smtp-server
SMTP_USER=your-email
SMTP_PASSWORD=your-email-password
FROM_EMAIL=your-sender-email
TO_EMAILS=recipient1@example.com,recipient2@example.com
```

## 🔍 Manual Investigation Queries

When you suspect account deactivation issues, run these queries:

### Find Recent Deactivations:
```sql
SELECT 
    id as publisher_id,
    name as publisher_name,
    status,
    inactivity_date,
    update_time,
    status_change_reason,
    TIMESTAMPDIFF(HOUR, COALESCE(inactivity_date, update_time), NOW()) as hours_ago
FROM publishers 
WHERE status = 'INACTIVE'
  AND (inactivity_date >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
       OR (inactivity_date IS NULL AND update_time >= DATE_SUB(NOW(), INTERVAL 24 HOUR)))
ORDER BY COALESCE(inactivity_date, update_time) DESC;
```

### Check Projects Under Specific Account:
```sql
SELECT 
    gep.project_id,
    gep.creation_date,
    c.syndicator_id,
    c.status as campaign_status
FROM geo_edge_projects gep
JOIN sp_campaigns c ON gep.campaign_id = c.id
WHERE c.syndicator_id = 'YOUR_ACCOUNT_ID_HERE';
```

## 📊 Monitoring & Alerts

### Key Metrics to Watch:
- **Newly Inactive Accounts**: Should be 0 most days
- **Priority Projects Reset**: Number of projects immediately set to (0,0)  
- **Baseline Age**: Should update daily
- **Email Delivery**: Verify reports are received

### Success Indicators:
- ✅ Email reports received daily at expected time
- ✅ "No newly inactive accounts found" in most reports
- ✅ When accounts do become inactive, immediate reset confirmation
- ✅ CSV exports include scan configuration details

## 🚨 Troubleshooting

### If Priority Detection Fails:
1. Check baseline file exists: `/tmp/account_status_baseline.json`
2. Verify database connectivity with: `python analyze_deactivation.py`
3. Check environment variables are set correctly

### If Email Reports Missing Information:
1. Verify SMTP credentials in environment
2. Check email template includes scan configuration columns
3. Run `python test_email.py` to test email functionality

### If Projects Not Being Reset:
1. Check GeoEdge API credentials in environment
2. Verify account IDs are correct format (strings)
3. Run with dry-run mode first to test

## 🎯 Expected Results

### Before Enhancement:
- Projects under inactive accounts continued scanning
- Manual monitoring required to catch account deactivations
- Delayed response to account status changes
- Basic email reports without scan configuration details

### After Enhancement:
- ⚡ **Immediate Detection**: Newly inactive accounts identified within hours
- 🔧 **Automatic Reset**: ALL projects under newly inactive accounts set to (0,0) immediately  
- 📧 **Detailed Reporting**: Enhanced emails with scan configuration tables and priority account highlighting
- 📊 **Proactive Monitoring**: Baseline comparison system prevents missed deactivations
- 💰 **Cost Savings**: Eliminates wasted scanning charges from inactive accounts

### Sample Success Report:
```
📊 INTEGRATED DAILY RESET COMPLETED
Priority accounts handled: 3
Total projects reset: 85 
✅ All newly inactive accounts have projects set to manual mode (0,0)
📧 Enhanced email report sent with CSV export
```

This system ensures that **any account becoming inactive will have ALL its projects immediately reset to manual mode (0,0)**, preventing continued automatic scanning and associated costs.