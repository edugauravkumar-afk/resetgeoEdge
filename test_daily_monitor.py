#!/usr/bin/env python3
"""
Test the daily inactive monitor system
This script runs the daily monitor in test mode
"""

import sys
import os
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from daily_inactive_monitor import DailyInactiveMonitor

def main():
    print("🧪 Testing Daily Inactive Monitor System")
    print("=" * 50)
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("")
    
    try:
        # Create monitor instance
        monitor = DailyInactiveMonitor()
        
        # Test database connection
        print("1. Testing database connection...")
        try:
            conn = monitor.get_database_connection()
            conn.close()
            print("   ✅ Database connection successful")
        except Exception as e:
            print(f"   ❌ Database connection failed: {e}")
            return False
        
        # Test getting configured accounts
        print("\n2. Testing account data retrieval...")
        try:
            accounts = monitor.get_all_configured_accounts()
            print(f"   ✅ Found {len(accounts)} configured accounts")
            print(f"   📊 Total projects: {monitor.stats['total_projects_configured']}")
        except Exception as e:
            print(f"   ❌ Failed to get account data: {e}")
            return False
        
        # Test activity check
        print("\n3. Testing account activity check...")
        try:
            if accounts:
                # Test with first few accounts
                test_accounts = list(accounts.keys())[:5]
                active, inactive = monitor.check_account_activity(test_accounts)
                print(f"   ✅ Activity check successful")
                print(f"   📊 Sample test: {len(active)} active, {len(inactive)} inactive (from {len(test_accounts)} tested)")
            else:
                print("   ⚠️ No accounts to test activity check")
        except Exception as e:
            print(f"   ❌ Activity check failed: {e}")
            return False
        
        # Test email configuration (don't actually send)
        print("\n4. Testing email configuration...")
        try:
            if monitor.email_config['sender_email'] and monitor.email_config['recipients']:
                print(f"   ✅ Email config found:")
                print(f"   📧 Sender: {monitor.email_config['sender_email']}")
                print(f"   📧 Recipients: {len(monitor.email_config['recipients'])} addresses")
            else:
                print("   ⚠️ Email configuration incomplete - please update .env file")
        except Exception as e:
            print(f"   ❌ Email configuration error: {e}")
        
        print("\n" + "=" * 50)
        print("🎯 Test Summary:")
        print("✅ System components are working correctly")
        print("📋 Ready for daily monitoring")
        
        # Ask if user wants to run actual monitoring
        print("\n" + "=" * 50)
        choice = input("🚀 Run actual daily monitoring now? (y/n): ").lower().strip()
        
        if choice == 'y':
            print("\n🔄 Running daily monitoring...")
            result = monitor.run_daily_check()
            
            if result['success']:
                print("\n✅ Daily monitoring completed successfully!")
                print(f"📊 Results:")
                print(f"   • New inactive accounts: {result['new_inactive_accounts']}")
                print(f"   • Projects reset to manual: {result['projects_reset']}")
                print(f"   • Total configured accounts: {result['stats']['total_configured_accounts']}")
                print(f"   • Total inactive accounts: {result['stats']['total_inactive_accounts']}")
            else:
                print(f"\n❌ Daily monitoring failed: {result['error']}")
                return False
        else:
            print("ℹ️  Skipping actual monitoring run")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)