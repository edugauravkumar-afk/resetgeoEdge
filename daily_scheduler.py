#!/usr/bin/env python3
"""
Daily GeoEdge Reset Scheduler
Runs the reset inactive accounts script daily at a specified time
"""

import schedule
import time
import subprocess
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Configuration
SCRIPT_DIR = Path(__file__).parent
LOG_DIR = SCRIPT_DIR / "logs"
SCHEDULE_TIME = "02:00"  # Run at 2:00 AM daily

# Setup logging
LOG_DIR.mkdir(exist_ok=True)
log_file = LOG_DIR / f"scheduler_{datetime.now().strftime('%Y%m%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

def run_reset_script():
    """Run the reset inactive accounts script"""
    try:
        logging.info("Starting daily reset job...")
        
        # Change to script directory
        os.chdir(SCRIPT_DIR)
        
        # Run the reset script
        cmd = [sys.executable, "reset_inactive_accounts.py", "--all-projects"]
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True,
            timeout=3600  # 1 hour timeout
        )
        
        if result.returncode == 0:
            logging.info("Daily reset job completed successfully")
            logging.info(f"Script output: {result.stdout}")
        else:
            logging.error(f"Daily reset job failed with exit code {result.returncode}")
            logging.error(f"Error output: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        logging.error("Daily reset job timed out after 1 hour")
    except Exception as e:
        logging.error(f"Unexpected error running daily reset job: {e}")

def main():
    """Main scheduler loop"""
    logging.info(f"Starting GeoEdge Reset Scheduler - will run daily at {SCHEDULE_TIME}")
    
    # Schedule the job
    schedule.every().day.at(SCHEDULE_TIME).do(run_reset_script)
    
    # Also run once immediately for testing (optional)
    if "--test" in sys.argv:
        logging.info("Running test execution...")
        run_reset_script()
        return
    
    logging.info(f"Scheduler started. Next run scheduled for {SCHEDULE_TIME}")
    
    # Keep the scheduler running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Scheduler stopped by user")
    except Exception as e:
        logging.error(f"Scheduler crashed: {e}")
        sys.exit(1)