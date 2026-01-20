#!/usr/bin/env python3
"""
Test the complete Auto Mode monitoring system
This tests the redesigned system that focuses on Auto Mode (1,72) accounts only
"""

import logging
import json
from datetime import datetime
from account_status_monitor import AccountStatusMonitor
from email_reporter import GeoEdgeEmailReporter
from daily_monitor_service import GeoEdgeDailyService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_auto_mode_account_detection():
    """Test the new Auto Mode account detection"""
    logger.info("🔍 Testing Auto Mode account detection...")
    
    monitor = AccountStatusMonitor()
    
    # Test getting active Auto Mode accounts
    auto_mode_accounts = monitor.get_active_auto_scan_accounts()
    logger.info(f"Found {len(auto_mode_accounts)} active Auto Mode accounts")
    
    if auto_mode_accounts:
        # Show first few examples
        for i, account in enumerate(auto_mode_accounts[:5]):
            logger.info(f"  Account {account['id']}: {account['name']} - {account['project_count']} projects")
        
        if len(auto_mode_accounts) > 5:
            logger.info(f"  ... and {len(auto_mode_accounts) - 5} more accounts")
    
    return auto_mode_accounts

def test_inactive_auto_mode_detection():
    """Test finding Auto Mode accounts that became inactive"""
    logger.info("🔍 Testing inactive Auto Mode account detection...")
    
    monitor = AccountStatusMonitor()
    
    # Test finding newly inactive Auto Mode accounts
    inactive_auto_accounts = monitor.find_newly_inactive_auto_scan_accounts()
    logger.info(f"Found {len(inactive_auto_accounts)} Auto Mode accounts that became inactive in last 24 hours")
    
    if inactive_auto_accounts:
        for account in inactive_auto_accounts:
            logger.info(f"  INACTIVE: Account {account['id']} - {account['project_count']} projects need reset")
    
    return inactive_auto_accounts

def test_complete_monitoring_system():
    """Test the complete monitoring flow"""
    logger.info("🔍 Testing complete Auto Mode monitoring system...")
    
    monitor = AccountStatusMonitor()
    
    # Run the complete monitoring check
    results = monitor.monitor_status_changes()
    
    logger.info("=== MONITORING RESULTS ===")
    logger.info(f"Auto Mode accounts monitored: {results.get('auto_mode_accounts_monitored', 0)}")
    logger.info(f"Accounts reset: {len(results.get('accounts_reset', []))}")
    logger.info(f"Total projects reset: {results.get('total_projects_reset', 0)}")
    
    accounts_reset = results.get('accounts_reset', [])
    if accounts_reset:
        logger.info("Accounts that were reset:")
        for account in accounts_reset:
            logger.info(f"  - Account {account['account_id']}: {account['projects_reset']} projects reset")
    else:
        logger.info("✅ No Auto Mode accounts needed to be reset")
    
    return results

def test_daily_service():
    """Test the daily service with Auto Mode focus"""
    logger.info("🔍 Testing daily service...")
    
    service = GeoEdgeDailyService()
    if not service.initialize():
        logger.error("❌ Failed to initialize daily service")
        return False
    
    # Run daily check
    try:
        service.run_daily_check()
        logger.info("✅ Daily service test completed successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Daily service test failed: {e}")
        return False

def test_email_with_mock_data():
    """Test email reporting with mock Auto Mode data"""
    logger.info("🔍 Testing email reporting with mock Auto Mode data...")
    
    # Mock data simulating 2 Auto Mode accounts that became inactive
    mock_report_data = {
        'status': 'success',
        'accounts_reset': [
            {
                'account_id': '1920118',
                'account_name': 'Test Auto Account 1',
                'status': 'PRIORITY_NEWLY_INACTIVE',
                'auto_scan': 0,  # Now set to manual
                'scans_per_day': 0,  # Now set to manual
                'total_projects': 25,
                'projects_reset': 25,  # All projects were reset
                'timestamp': datetime.now().isoformat()
            },
            {
                'account_id': '1920229',
                'account_name': 'Test Auto Account 2', 
                'status': 'PRIORITY_NEWLY_INACTIVE',
                'auto_scan': 0,
                'scans_per_day': 0,
                'total_projects': 18,
                'projects_reset': 18,
                'timestamp': datetime.now().isoformat()
            }
        ],
        'total_projects_reset': 43,
        'projects_reset': 43,
        'execution_time': 2.1,
        'total_accounts_monitored': 150,  # Only monitoring 150 Auto Mode accounts
        'inactive_accounts': 2,
        'active_accounts': 148,
        'projects_scanned': 43,
        'timestamp': datetime.now().isoformat()
    }
    
    reporter = GeoEdgeEmailReporter()
    
    # Send test email
    try:
        success = reporter.send_daily_reset_report(mock_report_data)
        if success:
            logger.info("✅ Test email sent successfully!")
            logger.info("📧 Check your email for 'GeoEdge Auto Mode Monitor' report")
        else:
            logger.error("❌ Failed to send test email")
        return success
    except Exception as e:
        logger.error(f"❌ Email test failed: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("🚀 Starting Auto Mode Monitoring System Tests")
    logger.info("=" * 60)
    
    try:
        # Test 1: Auto Mode account detection
        auto_accounts = test_auto_mode_account_detection()
        logger.info("")
        
        # Test 2: Inactive detection
        inactive_accounts = test_inactive_auto_mode_detection()
        logger.info("")
        
        # Test 3: Complete monitoring system
        monitoring_results = test_complete_monitoring_system()
        logger.info("")
        
        # Test 4: Daily service
        daily_service_ok = test_daily_service()
        logger.info("")
        
        # Test 5: Email with mock data
        email_ok = test_email_with_mock_data()
        logger.info("")
        
        # Summary
        logger.info("=" * 60)
        logger.info("🏁 TEST SUMMARY")
        logger.info(f"✅ Auto Mode accounts found: {len(auto_accounts) if auto_accounts else 0}")
        logger.info(f"⚠️  Currently inactive: {len(inactive_accounts) if inactive_accounts else 0}")
        logger.info(f"🔧 Projects reset today: {monitoring_results.get('total_projects_reset', 0) if monitoring_results else 0}")
        logger.info(f"🛠️  Daily service: {'✅ Working' if daily_service_ok else '❌ Failed'}")
        logger.info(f"📧 Email system: {'✅ Working' if email_ok else '❌ Failed'}")
        
        if email_ok and daily_service_ok:
            logger.info("🎉 AUTO MODE MONITORING SYSTEM IS READY!")
            logger.info("   You can now deploy this system on your Windows machine")
            logger.info("   It will monitor only Auto Mode (1,72) accounts and reset them when they become inactive")
        else:
            logger.error("⚠️  Some components need fixing before deployment")
        
    except Exception as e:
        logger.error(f"❌ Test execution failed: {e}")

if __name__ == "__main__":
    main()