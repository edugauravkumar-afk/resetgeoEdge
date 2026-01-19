#!/usr/bin/env python3
"""
Test Email Configuration for GeoEdge Reset System

This script tests the email configuration and sends a sample report
to verify that email notifications are working correctly.
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_email_config():
    """Check if all required email environment variables are configured"""
    required_vars = ['SMTP_SERVER', 'FROM_EMAIL', 'RECIPIENTS']
    missing_vars = []
    
    print("🔍 Checking email configuration...")
    
    for var in required_vars:
        value = os.getenv(var)
        if not value or not value.strip():
            missing_vars.append(var)
        else:
            print(f"  ✅ {var}: {value}")
    
    optional_vars = ['SMTP_PORT', 'SMTP_USER', 'SMTP_PASSWORD', 'CC_RECIPIENTS']
    for var in optional_vars:
        value = os.getenv(var)
        if value and value.strip():
            # Don't print passwords
            display_value = "***" if "PASSWORD" in var else value
            print(f"  ℹ️  {var}: {display_value}")
        else:
            print(f"  ➖ {var}: (not set)")
    
    if missing_vars:
        print(f"\n❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("\nPlease add them to your .env file:")
        for var in missing_vars:
            print(f"{var}=your_value_here")
        return False
    
    print("\n✅ Email configuration looks good!")
    return True


def send_test_email_no_changes():
    """Send a test email showing no changes in last 24 hours"""
    try:
        from email_reporter import GeoEdgeEmailReporter
        
        print("\n📧 Sending test email (NO CHANGES scenario)...")
        
        # Test data showing no recent changes
        test_data = {
            "total_accounts_checked": 0,  # No accounts processed
            "total_projects_reset": 0,   # No projects reset
            "execution_time": 5.2,
            "priority_reset_performed": False,
            "newly_inactive_count": 0,
            "accounts_reset": []  # Empty - no changes
        }
        
        reporter = GeoEdgeEmailReporter()
        success = reporter.send_daily_reset_report(test_data)
        
        if success:
            print("✅ Test email (no changes) sent successfully!")
            return True
        else:
            print("❌ Failed to send test email (no changes)")
            return False
            
    except Exception as e:
        print(f"❌ Error sending test email: {e}")
        return False
        
def send_test_email():
    """Send a test email to verify the configuration works"""
    try:
        from email_reporter import GeoEdgeEmailReporter
        
        print("\n📧 Sending test email...")
        
        # Create enhanced sample data showing ONLY last 24 hours changes
        test_data = {
            "total_accounts_checked": 3,  # Only accounts that were actually processed
            "total_projects_reset": 159,  # Total projects reset in last 24 hours
            "execution_time": 23.4,  # Float value for execution time
            "priority_reset_performed": True,
            "newly_inactive_count": 3,
            "accounts_reset": [
                # Priority newly inactive accounts (last 24h)
                {"account_id": "1878208", "account_name": "clevercrowads-sc", "auto_scan": 0, "scans_per_day": 0, "total_projects": 72, "status": "PRIORITY_NEWLY_INACTIVE", "projects_reset": 72},
                {"account_id": "1953730", "account_name": "level-upadsco-sc", "auto_scan": 0, "scans_per_day": 0, "total_projects": 46, "status": "PRIORITY_NEWLY_INACTIVE", "projects_reset": 46},  
                {"account_id": "1878374", "account_name": "tiagodemcardoso-account", "auto_scan": 0, "scans_per_day": 0, "total_projects": 41, "status": "PRIORITY_NEWLY_INACTIVE", "projects_reset": 41},
                
                # NOTE: Removed regular inactive accounts with no recent changes
                # Only showing accounts that had actual project resets in last 24h
            ]
        }
        
        reporter = GeoEdgeEmailReporter()
        success = reporter.send_daily_reset_report(test_data)
        
        if success:
            print("✅ Test email sent successfully!")
            print("📬 Check your email inbox (and spam folder) for the test report")
            return True
        else:
            print("❌ Failed to send test email")
            return False
            
    except ImportError as e:
        print(f"❌ Cannot import email_reporter: {e}")
        print("Make sure email_reporter.py is in the same directory")
        return False
    except Exception as e:
        print(f"❌ Error sending test email: {e}")
        return False


def test_smtp_connection():
    """Test basic SMTP connection without sending email"""
    import smtplib
    
    try:
        smtp_server = os.getenv('SMTP_SERVER')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        smtp_user = os.getenv('SMTP_USER')
        smtp_password = os.getenv('SMTP_PASSWORD')
        
        print(f"\n🔌 Testing SMTP connection to {smtp_server}:{smtp_port}...")
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            # Use STARTTLS for port 587
            if smtp_port == 587:
                server.starttls()
                print("  ✅ STARTTLS established")
            
            # Login if credentials provided
            if smtp_user and smtp_password:
                server.login(smtp_user, smtp_password)
                print("  ✅ Authentication successful")
            else:
                print("  ℹ️  No authentication (using anonymous connection)")
        
        print("✅ SMTP connection test successful!")
        return True
        
    except Exception as e:
        print(f"❌ SMTP connection failed: {e}")
        return False


def main():
    """Run all email tests"""
    print("🚀 GeoEdge Email Configuration Test")
    print("=" * 50)
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("❌ .env file not found!")
        print("Please create a .env file with your email configuration.")
        print("\nExample .env file:")
        print("""
SMTP_SERVER=your-smtp-server.com
SMTP_PORT=587
SMTP_USER=your-email@company.com
SMTP_PASSWORD=your-password
FROM_EMAIL=your-email@company.com
RECIPIENTS=recipient1@company.com,recipient2@company.com
CC_RECIPIENTS=manager@company.com
        """.strip())
        return 1
    
    # Step 1: Check configuration
    if not check_email_config():
        return 1
    
    # Step 2: Test SMTP connection
    if not test_smtp_connection():
        print("\n⚠️  SMTP connection failed, but continuing with email test...")
        print("(Some internal SMTP servers may reject connection tests)")
    
# Step 3: Send test emails for both scenarios
    print("\n📧 TESTING: Email with Recent Changes (Last 24H)")
    print("="*50)
    changes_success = send_test_email()
    
    if not changes_success:
        return 1
    
    # Wait a moment then test no changes scenario
    import time
    time.sleep(2)
    
    print("\n📧 TESTING: Email with No Changes Scenario")
    print("="*50)
    no_changes_success = send_test_email_no_changes()
    
    if not no_changes_success:
        return 1

    print("\n🎉 All email tests passed!")
    print("\n📋 Next Steps:")
    print("1. Check your email for BOTH test reports")
    print("2. First email: Shows recent changes in last 24 hours only")
    print("3. Second email: Shows 'no changes' scenario")
    print("4. The daily reset script will automatically send reports")
    print("5. Email reports include:")
    print("   - Only accounts with changes in last 24 hours")
    print("   - Priority newly inactive account alerts")
    print("   - Project scan configuration details")
    print("   - CSV attachment with recent changes only")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())