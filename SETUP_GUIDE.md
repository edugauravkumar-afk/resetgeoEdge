# GeoEdge Reset Inactive Accounts Script - Setup Guide

## Files Required

Your team member will need these files from your project:

### Core Files:
1. **`reset_inactive_accounts.py`** - Main script
2. **`update_autoscan.py`** - API update functions
3. **`geoedge_projects/`** - Client library folder
   - `__init__.py`
   - `client.py`
4. **`requirements.txt`** - Python dependencies
5. **`.env`** - Environment configuration (copy from your working version)

## Setup Instructions

### 1. Copy Files to Their System
Place all the provided files in their working directory maintaining the structure:
```
their-working-directory/
├── reset_inactive_accounts.py
├── update_autoscan.py
├── requirements.txt
├── .env
└── geoedge_projects/
    ├── __init__.py
    └── client.py
```

### 2. Install Dependencies
```bash
# Install required packages (if not already installed)
pip install -r requirements.txt
```

### 3. Configure Environment
The `.env` file should contain these credentials:
```env
# GeoEdge API Configuration
GEOEDGE_API_KEY=actual_api_key_here
GEOEDGE_API_BASE=https://api.geoedge.com/v3.5.1

# MySQL Database Configuration  
MYSQL_HOST=mysql_host
MYSQL_PORT=3306
MYSQL_USER=mysql_username
MYSQL_PASSWORD=mysql_password
MYSQL_DB=trc
```

## Running the Script

### Test Run First (Recommended):
```bash
python reset_inactive_accounts.py --dry-run
```
This will show what would be changed without making actual changes.

### Live Run (Make Actual Changes):
```bash
python reset_inactive_accounts.py
```
This will reset projects from auto mode (1,72) to manual mode (0,0) for inactive accounts.

### Advanced Options:
```bash
# Reset ALL projects for both active and inactive accounts
python reset_inactive_accounts.py --all-projects

# Use custom account list from file
python reset_inactive_accounts.py --accounts-file my_accounts.txt

# Change lookback period for active accounts (default 30 days)
python reset_inactive_accounts.py --days 60
```

## What the Script Does

1. **Identifies inactive accounts** (frozen, paused, depleted)
2. **Fetches ALL projects** for inactive accounts (no time limit)
3. **Fetches recent projects** for active accounts (last 30 days by default)
4. **Scans configurations** to find projects not set to (0,0)
5. **Resets projects** from any non-zero configuration (like 1,72) to manual mode (0,0)
6. **Provides detailed logging** showing which accounts/projects are being processed

## Expected Output

### When projects need resetting:
```
Detected 4 frozen accounts and 93 live accounts
🚨 HIGH PRIORITY: project_123 (INACTIVE acct 1234567) config 1,72 -> NEEDS RESET
Resetting 15 projects from auto mode to manual mode (0,0)
Projects changed from auto mode (1,72) to manual (0,0): 15
```

### When all projects are already correct:
```
Detected 4 frozen accounts and 93 live accounts
🎯 Priority: Resetting ALL projects for 4 inactive accounts
✅ All projects are already properly configured (0,0)!
```

## Quick Command Reference

```bash
# Test what would be changed (SAFE - no actual changes)
python reset_inactive_accounts.py --dry-run

# Actually make the changes
python reset_inactive_accounts.py

# Reset ALL projects (not just inactive accounts)
python reset_inactive_accounts.py --all-projects
```

## Troubleshooting

- **Database connection issues**: Verify MySQL credentials in `.env`
- **API errors**: Check GeoEdge API key and base URL
- **Import errors**: Ensure all files are in correct directory structure
- **Permission errors**: Make sure the API key has project update permissions

## Security Notes

- Keep `.env` file secure and never commit it to version control
- Use environment-specific credentials
- Test with `--dry-run` first before making actual changes