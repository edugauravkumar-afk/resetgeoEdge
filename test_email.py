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


def send_test_email():
    """Send a test email to verify the configuration works"""
    try:
        from email_reporter import GeoEdgeEmailReporter
        
        print("\n📧 Sending test email...")
        
        # Create realistic sample report data
        test_data = {
            "total_accounts_checked": 97,
            "inactive_accounts": 4,
            "active_accounts": 93, 
            "total_projects_scanned": 1025,
            "projects_reset": 0,
            "execution_time": 42.5,
            "status": "success",
            "inactive_account_details": [
                {"account_id": "1290644", "status": "INACTIVE", "project_count": 150, "changes_made": 0, "auto_scan": 0, "scans_per_day": 0},
                {"account_id": "1466060", "status": "INACTIVE", "project_count": 200, "changes_made": 0, "auto_scan": 0, "scans_per_day": 0},
                {"account_id": "1835770", "status": "INACTIVE", "project_count": 125, "changes_made": 0, "auto_scan": 0, "scans_per_day": 0},
                {"account_id": "1623554", "status": "INACTIVE", "project_count": 178, "changes_made": 0, "auto_scan": 0, "scans_per_day": 0},
            ],
            "active_account_details": [
                {"account_id": "1787788", "status": "ACTIVE", "project_count": 1, "changes_made": 0, "auto_scan": 1, "scans_per_day": 72},
                {"account_id": "1798665", "status": "ACTIVE", "project_count": 1, "changes_made": 0, "auto_scan": 1, "scans_per_day": 72},
                {"account_id": "1813037", "status": "ACTIVE", "project_count": 2, "changes_made": 0, "auto_scan": 1, "scans_per_day": 72},
                {"account_id": "1813041", "status": "ACTIVE", "project_count": 4, "changes_made": 0, "auto_scan": 1, "scans_per_day": 72},
                {"account_id": "1823276", "status": "ACTIVE", "project_count": 16, "changes_made": 0, "auto_scan": 1, "scans_per_day": 72},
                {"account_id": "1828308", "status": "ACTIVE", "project_count": 1, "changes_made": 0, "auto_scan": 1, "scans_per_day": 72},
                {"account_id": "1829970", "status": "ACTIVE", "project_count": 6, "changes_made": 0, "auto_scan": 1, "scans_per_day": 72},
                {"account_id": "1829976", "status": "ACTIVE", "project_count": 4, "changes_made": 0, "auto_scan": 1, "scans_per_day": 72},
                {"account_id": "1847769", "status": "ACTIVE", "project_count": 6, "changes_made": 0, "auto_scan": 1, "scans_per_day": 72},
                {"account_id": "1867619", "status": "ACTIVE", "project_count": 6, "changes_made": 0, "auto_scan": 1, "scans_per_day": 72},
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
    
    # Step 3: Send test email
    if not send_test_email():
        return 1
    
    print("\n🎉 All email tests passed!")
    print("\n📋 Next Steps:")
    print("1. Check your email for the test report")
    print("2. If you received it, email notifications are working!")
    print("3. The daily reset script will automatically send reports")
    print("4. Email reports include:")
    print("   - Account processing summary")
    print("   - Project scan results") 
    print("   - Configuration changes made")
    print("   - CSV attachment with detailed data")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())