#!/usr/bin/env python3
"""
Send Demo Auto Mode Status Email
Demonstrates the monitoring system with realistic sample data
"""

import logging
from datetime import datetime
from email_reporter import GeoEdgeEmailReporter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def send_demo_auto_mode_report():
    """Send demo email showing Auto Mode monitoring capabilities"""
    
    # Create realistic demo data showing what the system would detect
    demo_report_data = {
        'status': 'success',
        'accounts_reset': [
            {
                'account_id': '1920118',
                'account_name': 'Example Auto Mode Account 1',
                'status': 'PRIORITY_NEWLY_INACTIVE', 
                'auto_scan': 0,  # Now set to manual after reset
                'scans_per_day': 0,  # Now set to manual after reset
                'total_projects': 45,
                'projects_reset': 45,  # All 45 projects were reset from (1,72) to (0,0)
                'timestamp': '2026-01-20T15:30:00'
            },
            {
                'account_id': '1856234',
                'account_name': 'Auto Scan Publisher Demo',
                'status': 'PRIORITY_NEWLY_INACTIVE',
                'auto_scan': 0,  # Now manual
                'scans_per_day': 0,  # Now manual  
                'total_projects': 28,
                'projects_reset': 28,  # All 28 projects reset
                'timestamp': '2026-01-20T14:45:00'
            },
            {
                'account_id': '1734567',
                'account_name': 'Sample Client Auto Config',
                'status': 'PRIORITY_NEWLY_INACTIVE',
                'auto_scan': 0,
                'scans_per_day': 0,
                'total_projects': 17,
                'projects_reset': 17,
                'timestamp': '2026-01-20T13:20:00'
            }
        ],
        'total_projects_reset': 90,  # 45 + 28 + 17 = 90 projects reset
        'projects_reset': 90,
        'execution_time': 2.8,
        'total_accounts_monitored': 347,  # Total Auto Mode accounts being monitored
        'inactive_accounts': 3,  # These 3 accounts became inactive
        'active_accounts': 344,  # 347 - 3 = 344 still active
        'projects_scanned': 90,
        'timestamp': datetime.now().isoformat()
    }
    
    print("📧 Sending demo Auto Mode monitoring report...")
    print("🔍 This demonstrates what the system would detect and report:")
    print(f"   • Auto Mode accounts monitored: {demo_report_data['total_accounts_monitored']}")
    print(f"   • Accounts that became inactive: {demo_report_data['inactive_accounts']}")  
    print(f"   • Projects reset from (1,72) to (0,0): {demo_report_data['total_projects_reset']}")
    print()
    
    try:
        reporter = GeoEdgeEmailReporter()
        success = reporter.send_daily_reset_report(demo_report_data)
        
        if success:
            print("✅ DEMO EMAIL SENT SUCCESSFULLY!")
            print("📧 Check your email for 'GeoEdge Auto Mode Monitor' report")
            print()
            print("📋 The email demonstrates:")
            print("   ✓ Professional Auto Mode monitoring report")
            print("   ✓ Account details with project counts") 
            print("   ✓ Summary statistics (Auto Mode Accounts: 347, Became Inactive: 3)")
            print("   ✓ Projects Reset: 90 projects changed from (1,72) to (0,0)")
            print("   ✓ CSV export with complete data")
            print("   ✓ Priority account highlighting")
            print()
            print("🎯 This is exactly what you'll receive daily when accounts become inactive!")
            
        else:
            print("❌ Failed to send demo email")
            
        return success
        
    except Exception as e:
        logger.error(f"Error sending demo email: {e}")
        print(f"❌ Error: {e}")
        return False

def main():
    print("🚀 GeoEdge Auto Mode Monitoring System - Demo Report")
    print("=" * 60)
    print("This will send you a demonstration email showing:")
    print("• How the system detects Auto Mode accounts that become inactive") 
    print("• Automatic project reset from Auto Mode (1,72) to Manual Mode (0,0)")
    print("• Professional email reporting with statistics")
    print("• CSV data export for record keeping")
    print("=" * 60)
    print()
    
    success = send_demo_auto_mode_report()
    
    if success:
        print()
        print("🎉 SUCCESS! Demo email sent to gaurav.k@taboola.com")
        print()
        print("📋 Next Steps:")
        print("1. Check your email inbox for the Auto Mode monitoring report") 
        print("2. Review the account details and project reset information")
        print("3. The system is ready for Windows deployment")
        print("4. Follow AUTO_MODE_DEPLOYMENT_GUIDE.md for setup")
        print()
        print("🔄 When deployed, this system will:")
        print("   • Run automatically daily at 9:00 AM")
        print("   • Monitor ONLY Auto Mode (1,72) accounts")
        print("   • Reset projects to (0,0) when accounts become inactive") 
        print("   • Send you daily reports with actual changes")

if __name__ == "__main__":
    main()