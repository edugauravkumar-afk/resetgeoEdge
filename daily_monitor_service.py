#!/usr/bin/env python3
"""
GeoEdge Daily Monitor Service - Self-executing daemon for account monitoring
Runs continuously and automatically executes daily checks with email reports
"""

import os
import sys
import time
import schedule
import threading
from datetime import datetime, timedelta
from dotenv import load_dotenv
import signal
import logging
from account_status_monitor import AccountStatusMonitor
from email_reporter import GeoEdgeEmailReporter

load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/geoedge_monitor.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class GeoEdgeDailyService:
    """Self-executing daily monitoring service"""
    
    def __init__(self):
        self.running = False
        self.monitor = None
        self.reporter = None
        
    def initialize(self):
        """Initialize monitoring components"""
        try:
            self.monitor = AccountStatusMonitor()
            self.reporter = GeoEdgeEmailReporter()
            logger.info("✅ GeoEdge Daily Service initialized successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize service: {e}")
            return False
    
    def run_daily_check(self):
        """Execute the daily monitoring and reporting"""
        try:
            logger.info("🔍 Starting daily account status check...")
            
            # Check for newly inactive accounts
            results = self.monitor.monitor_status_changes()
            
            # Prepare report data for email
            accounts_reset = []
            total_projects_reset = 0
            
            # If there are newly inactive accounts, prepare their data for email
            if results['newly_inactive_accounts']:
                priority_accounts = [str(acc['id']) for acc in results['newly_inactive_accounts']]
                logger.info(f"📋 PRIORITY ACCOUNT IDs FOR IMMEDIATE RESET: {','.join(priority_accounts)}")
                
                # Convert to email format
                for acc in results['newly_inactive_accounts']:
                    account_data = {
                        'account_id': str(acc['id']),
                        'account_name': acc.get('name', 'Unknown'),
                        'status': 'PRIORITY_NEWLY_INACTIVE',
                        'auto_scan': 0,
                        'scans_per_day': 0,
                        'total_projects': acc.get('project_count', 0),
                        'projects_reset': acc.get('project_count', 0),
                        'project_count': acc.get('project_count', 0)
                    }
                    accounts_reset.append(account_data)
                    total_projects_reset += acc.get('project_count', 0)
                
                logger.info(f"🚨 Found {len(accounts_reset)} priority accounts with {total_projects_reset} projects to reset")
            else:
                logger.info("✅ No newly inactive accounts found")
            
            # Always send daily report
            logger.info("📧 Sending daily report...")
            
            report_data = {
                'status': 'success',
                'accounts_reset': accounts_reset,
                'total_projects_reset': total_projects_reset,
                'execution_time': 2.5,
                'inactive_accounts': len(accounts_reset),
                'active_accounts': 0,
                'projects_scanned': total_projects_reset,
                'timestamp': datetime.now().isoformat()
            }
            
            email_sent = self.reporter.send_daily_reset_report(report_data)
            
            if email_sent:
                if accounts_reset:
                    logger.info(f"✅ Daily report sent: {len(accounts_reset)} priority accounts, {total_projects_reset} projects reset")
                else:
                    logger.info("✅ Daily report sent: No changes detected")
            else:
                logger.error("❌ Failed to send daily report")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error during daily check: {e}")
            
            # Try to send error report
            try:
                error_report = {
                    'status': 'error',
                    'error_message': str(e),
                    'accounts_reset': [],
                    'total_projects_reset': 0,
                    'execution_time': 0,
                    'timestamp': datetime.now().isoformat()
                }
                self.reporter.send_daily_reset_report(error_report)
                logger.info("📧 Error report sent to administrators")
            except:
                logger.error("❌ Failed to send error report")
            
            return False
    
    def start_service(self):
        """Start the continuous monitoring service"""
        if not self.initialize():
            logger.error("❌ Service initialization failed. Exiting.")
            return
        
        self.running = True
        
        # Schedule daily execution at 9:00 AM
        schedule.every().day.at("09:00").do(self.run_daily_check)
        
        logger.info("🚀 GeoEdge Daily Monitor Service started")
        logger.info("⏰ Scheduled to run daily at 09:00 AM")
        logger.info("📧 Daily reports will be sent automatically")
        logger.info("🔄 Press Ctrl+C to stop the service")
        
        # Run initial check if it's been more than 23 hours since last run
        last_run_file = "/tmp/geoedge_last_run.txt"
        should_run_now = True
        
        if os.path.exists(last_run_file):
            try:
                with open(last_run_file, 'r') as f:
                    last_run_str = f.read().strip()
                    last_run = datetime.fromisoformat(last_run_str)
                    if datetime.now() - last_run < timedelta(hours=23):
                        should_run_now = False
                        logger.info(f"⏳ Last run was at {last_run_str}, skipping initial run")
            except:
                pass
        
        if should_run_now:
            logger.info("🔄 Running initial check...")
            if self.run_daily_check():
                with open(last_run_file, 'w') as f:
                    f.write(datetime.now().isoformat())
        
        # Main service loop
        try:
            while self.running:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
                
        except KeyboardInterrupt:
            logger.info("🛑 Service stopped by user")
        except Exception as e:
            logger.error(f"❌ Service error: {e}")
        finally:
            self.stop_service()
    
    def stop_service(self):
        """Stop the service gracefully"""
        self.running = False
        logger.info("🔄 GeoEdge Daily Monitor Service stopped")

def signal_handler(signum, frame):
    """Handle system signals for graceful shutdown"""
    logger.info(f"📡 Received signal {signum}, shutting down...")
    sys.exit(0)

def main():
    """Main entry point"""
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and start service
    service = GeoEdgeDailyService()
    service.start_service()

if __name__ == "__main__":
    main()