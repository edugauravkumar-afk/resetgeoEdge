# Daily GeoEdge Reset Scheduler Setup Guide

## Two Options Available

### Option 1: Cron Job (Recommended for macOS/Linux)

#### Setup Cron Job:
```bash
# Edit crontab
crontab -e

# Add this line to run daily at 2:00 AM
0 2 * * * /Users/gaurav.k/Desktop/geoedge-country-projects/daily_reset.sh

# Save and exit
```

#### Manual Test:
```bash
# Test the script manually
./daily_reset.sh
```

#### View Logs:
```bash
# Check recent logs
ls -la logs/daily_reset_*.log
tail -f logs/daily_reset_*.log
```

---

### Option 2: Python Scheduler (Alternative)

#### Install Additional Dependency:
```bash
pip install schedule
```

#### Run Scheduler:
```bash
# Start the scheduler (runs continuously)
python daily_scheduler.py

# Test run (runs once immediately)
python daily_scheduler.py --test
```

#### Run as Background Service:
```bash
# Run in background
nohup python daily_scheduler.py > logs/scheduler.log 2>&1 &

# Check if running
ps aux | grep daily_scheduler
```

---

## What the Scheduler Does

1. **Daily Execution**: Runs at 2:00 AM every day
2. **Account Check**: Identifies all inactive accounts
3. **Project Reset**: Changes ALL projects under inactive accounts from any config (like 1,72) to manual mode (0,0)
4. **Comprehensive Logging**: Logs all activities with timestamps
5. **Error Handling**: Captures and logs any errors

## Configuration

### Change Schedule Time:
- **Cron**: Edit the cron line (0 2 * * * = 2:00 AM)
- **Python**: Edit `SCHEDULE_TIME = "02:00"` in `daily_scheduler.py`

### Change Script Location:
- Update `SCRIPT_DIR` path in both files

## Monitoring

### View Recent Activity:
```bash
# Show latest log files
ls -la logs/
tail -20 logs/daily_reset_$(date +%Y%m%d)*.log
```

### Check Scheduler Status:
```bash
# For cron jobs
crontab -l

# For Python scheduler
ps aux | grep daily_scheduler
```

## Output Examples

### Successful Run:
```
=== Daily Reset Job Started: Sun Jan 19 02:00:01 2026 ===
Detected 4 frozen accounts and 93 live accounts
🎯 Priority: Resetting ALL projects for 4 inactive accounts
✅ All projects are already properly configured (0,0)!
=== Daily Reset Job Completed Successfully: Sun Jan 19 02:00:15 2026 ===
```

### When Projects Are Reset:
```
=== Daily Reset Job Started: Mon Jan 20 02:00:01 2026 ===
🚨 HIGH PRIORITY: project_123 (INACTIVE acct 1234567) config 1,72 -> NEEDS RESET
Projects changed from auto mode (1,72) to manual (0,0): 5
=== Daily Reset Job Completed Successfully: Mon Jan 20 02:00:45 2026 ===
```