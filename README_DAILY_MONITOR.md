# Daily Inactive Account Monitor

An automated system that monitors GeoEdge accounts for inactivity and automatically converts their projects from Auto Mode (1,72) to Manual Mode (0,0) to optimize resource usage.

## 🎯 Overview

This system runs daily to:
1. **Identify newly inactive accounts** (no alerts in 30+ days)
2. **Reset their projects** from Auto Mode (1,72) to Manual Mode (0,0)
3. **Send comprehensive email reports** with detailed statistics
4. **Track changes over time** and maintain historical state

## 📊 Email Report Includes

The daily email report provides comprehensive statistics:

### Overall System Statistics
- Total configured accounts (X)
- Total configured projects (Y) 
- Total inactive accounts (Z)
- Total inactive projects set to (0,0) (Z1)
- Total active accounts (A)
- Total active projects with (1,72) config (B)

### Daily Activity Summary
- New inactive accounts found in last 24hrs (D)
- Total projects found under new inactive accounts (F)
- Projects successfully updated to (0,0) configuration
- Remaining active accounts and projects
- Success/failure rates for API updates

### Visual Report Features
- Color-coded statistics boxes
- Progress tracking tables
- Error reporting with details
- Historical comparison data

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Install dependencies (if not already done)
pip install -r requirements.txt

# Configure email settings in .env file
nano .env
```

### 2. Configure Email Settings

Update the `.env` file with your email configuration:

```env
# Daily Monitor Email Configuration
SENDER_EMAIL=your_alerts@company.com
SENDER_PASSWORD=your_app_password_or_token
RECIPIENT_EMAILS=admin@company.com,manager@company.com

# Database Configuration (already configured)
DB_HOST=proxysql-office.taboolasyndication.com
DB_PORT=6033
DB_USER=gaurav.k
DB_PASSWORD=Hare_1317
DB_NAME=TRC
```

### 3. Test the System

```bash
# Run comprehensive test
python test_daily_monitor.py

# Or test individual components
python daily_inactive_monitor.py
```

### 4. Setup Daily Scheduling

```bash
# Run the scheduler setup script
chmod +x setup_daily_scheduler.sh
./setup_daily_scheduler.sh
```

This will:
- Create a wrapper script for cron execution
- Set up logging directory
- Provide cron job configuration instructions

### 5. Configure Cron Job

Add to your crontab (`crontab -e`):

```bash
# Run daily at 9:00 AM
0 9 * * * /path/to/geoedge-country-projects/run_daily_monitor.sh

# Alternative schedules:
# 0 6 * * *   # 6:00 AM daily
# 30 8 * * *  # 8:30 AM daily  
# 0 22 * * *  # 10:00 PM daily
```

## 📁 File Structure

```
geoedge-country-projects/
├── daily_inactive_monitor.py      # Main monitoring script
├── test_daily_monitor.py          # Testing utility
├── setup_daily_scheduler.sh       # Scheduler setup
├── run_daily_monitor.sh          # Cron wrapper (auto-generated)
├── daily_monitor_state.json      # State tracking file
├── logs/                         # Log files directory
│   ├── daily_monitor_20260120.log
│   └── daily_monitor_YYYYMMDD.log
└── .env                          # Configuration file
```

## 🔧 Configuration Options

### Email Configuration

- **SMTP_SERVER**: Email server (default: smtp.gmail.com)
- **SMTP_PORT**: Email server port (default: 587)
- **SENDER_EMAIL**: From email address
- **SENDER_PASSWORD**: Email password/app token
- **RECIPIENT_EMAILS**: Comma-separated recipient list

### Database Configuration

- **DB_HOST**: MySQL host
- **DB_PORT**: MySQL port
- **DB_USER**: MySQL username
- **DB_PASSWORD**: MySQL password
- **DB_NAME**: Database name (TRC)

### GeoEdge API Configuration

- **GEOEDGE_API_KEY**: API authentication key
- **GEOEDGE_API_BASE**: API base URL

## 📊 Monitoring Logic

### Account Activity Detection
- **Active Account**: Has alerts in the last 30 days
- **Inactive Account**: No alerts in the last 30+ days
- **Newly Inactive**: Was active yesterday, inactive today

### Project Reset Process
1. Query database for accounts with Auto Mode projects (1,72)
2. Check activity status via alerts table
3. Identify newly inactive accounts
4. Get all projects for these accounts
5. Update each project via GeoEdge API to Manual Mode (0,0)
6. Track success/failure rates
7. Generate comprehensive report

### State Management
The system maintains state in `daily_monitor_state.json`:
- Previous inactive account list
- Last check timestamp
- Historical statistics
- Trend tracking data

## 🚨 Error Handling

### Automatic Recovery
- Database connection retries
- API timeout handling with delays
- Email fallback on system errors
- Comprehensive logging

### Failure Notifications
- Failed API updates are logged and emailed
- System errors trigger immediate email alerts
- All operations are logged with timestamps

### Manual Recovery
```bash
# Check recent logs
tail -f logs/daily_monitor_$(date +%Y%m%d).log

# Reset state file (if needed)
rm daily_monitor_state.json

# Manual test run
python test_daily_monitor.py
```

## 📈 Statistics Tracking

The system tracks comprehensive metrics:

```python
{
    "run_timestamp": "2026-01-20T18:58:17",
    "total_configured_accounts": 3534,
    "total_projects_configured": 15420,
    "total_inactive_accounts": 197,
    "total_inactive_projects": 2021,
    "total_active_accounts": 3337,
    "total_active_projects": 13399,
    "new_inactive_accounts_24h": 5,
    "new_inactive_projects_24h": 23,
    "projects_reset_to_manual": 23,
    "reset_success_count": 23,
    "reset_failure_count": 0
}
```

## 🔍 Troubleshooting

### Common Issues

1. **Database Connection Failed**
   ```bash
   # Check VPN connection to Taboola network
   # Verify database credentials in .env
   ```

2. **Email Not Sending**
   ```bash
   # Verify SMTP settings
   # Check sender email app password
   # Test with test_daily_monitor.py
   ```

3. **API Updates Failing**
   ```bash
   # Verify GeoEdge API key
   # Check API rate limits
   # Review project IDs in logs
   ```

4. **Cron Job Not Running**
   ```bash
   # Check cron service: sudo systemctl status cron
   # Verify crontab entry: crontab -l
   # Test wrapper script manually
   ```

### Log Analysis

```bash
# View today's log
cat logs/daily_monitor_$(date +%Y%m%d).log

# Check for errors
grep -i error logs/daily_monitor_*.log

# Monitor real-time
tail -f logs/daily_monitor_$(date +%Y%m%d).log
```

## 🎯 Performance

- **Execution Time**: ~2 hours for 2,000 projects (2-second API delays)
- **Resource Usage**: Minimal CPU/memory impact
- **API Rate Limiting**: 2-second delays between calls
- **Database Impact**: Read-only queries, minimal load

## 🔮 Future Enhancements

Potential improvements:
- Slack/Teams notifications
- Dashboard web interface  
- Custom inactivity thresholds
- Project-level activity analysis
- Automated re-activation detection
- Historical trend visualization

---

## 📞 Support

For issues or questions:
1. Check the logs in `logs/` directory
2. Run `python test_daily_monitor.py` for diagnostics
3. Review the state file `daily_monitor_state.json`
4. Contact the system administrator

---

*Generated by GeoEdge Daily Monitoring System v1.0*