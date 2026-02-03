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
from account_status_monitor_fixed import AccountStatusMonitor
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
        """Execute the comprehensive daily monitoring (Auto Mode + APcampaign) and reporting"""
        try:
            logger.info("🔍 Starting comprehensive daily monitoring (Auto Mode + APcampaign)...")
            
            # Run comprehensive monitoring that includes both Auto Mode and APcampaign
            results = self.monitor.monitor_status_changes()
            
            # Extract Auto Mode results
            accounts_reset = results.get('accounts_reset', [])
            total_projects_reset = results.get('total_projects_reset', 0)
            auto_mode_accounts_monitored = results.get('auto_mode_accounts_monitored', 0)
            
            # Extract APcampaign results
            apcampaign_accounts_reset = results.get('apcampaign_accounts_reset', [])
            apcampaign_projects_reset = results.get('apcampaign_projects_reset', 0)
            apcampaign_projects_monitored = results.get('apcampaign_projects_monitored', 0)
            
            # Combined totals
            total_all_projects_reset = results.get('total_all_projects_reset', total_projects_reset + apcampaign_projects_reset)
            
            # Extract Non-Matching reset results (Phase 4)
            non_matching_checked = results.get('non_matching_checked', 0)
            non_matching_reset = results.get('non_matching_reset', 0)
            
            # Log Auto Mode results
            if accounts_reset:
                logger.info(f"🚨 Auto Mode: Found {len(accounts_reset)} accounts that became inactive")
                logger.info(f"🔧 Auto Mode: Reset {total_projects_reset} projects from (1,72) to (0,0)")
                
                for account in accounts_reset:
                    logger.info(f"   Auto Mode Reset Account {account['account_id']}: {account['projects_reset']} projects")
            else:
                logger.info("✅ Auto Mode: No accounts became inactive")
            
            # Log APcampaign results  
            if apcampaign_accounts_reset:
                logger.info(f"🚨 APcampaign: Found {len(apcampaign_accounts_reset)} projects with inactive accounts")
                logger.info(f"🔧 APcampaign: Reset {apcampaign_projects_reset} projects from (1,12) to (0,0)")
            else:
                logger.info("✅ APcampaign: All accounts remain active")
            
            # Log Non-Matching results (Phase 4)
            if non_matching_reset > 0:
                logger.info(f"🔧 Non-Matching: Reset {non_matching_reset} projects (auto mode with inactive campaigns/accounts)")
            else:
                logger.info(f"✅ Non-Matching: Checked {non_matching_checked} projects - all properly configured")
            
            # Combined summary
            logger.info(f"📊 TOTAL: {total_all_projects_reset} projects reset across all monitoring types")
            
            # Always send comprehensive daily report
            logger.info("📧 Sending comprehensive daily monitoring report...")
            
            # Pass all results to email reporter (it's already updated to handle comprehensive data)
            email_sent = self.reporter.send_daily_reset_report(results)
            
            if email_sent:
                if total_all_projects_reset > 0:
                    logger.info(f"✅ Comprehensive report sent: Auto:{total_projects_reset} + APcampaign:{apcampaign_projects_reset} + NonMatching:{non_matching_reset} = {total_all_projects_reset} projects reset")
                else:
                    logger.info("✅ Comprehensive report sent: No changes detected")
            else:
                logger.error("❌ Failed to send comprehensive report")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error during comprehensive daily check: {e}")
            
            # Try to send error report
            try:
                error_report = {
                    'status': 'error',
                    'error_message': str(e),
                    'accounts_reset': [],
                    'total_projects_reset': 0,
                    'apcampaign_accounts_reset': [],
                    'apcampaign_projects_reset': 0,
                    'total_all_projects_reset': 0,
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