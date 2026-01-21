#!/usr/bin/env python3
"""
Debug script to check what email recipients are being read from environment
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def debug_email_config():
    """Debug email configuration"""
    print("🔍 DEBUG: Email Configuration Analysis")
    print("=" * 50)
    
    # Check .env file existence
    env_file = '.env'
    if os.path.exists(env_file):
        print(f"✅ .env file found: {os.path.abspath(env_file)}")
    else:
        print("❌ .env file not found")
    
    # Check all email-related environment variables
    email_vars = [
        'RECIPIENTS', 
        'RECIPIENT_EMAILS', 
        'CC_RECIPIENTS',
        'SENDER_EMAIL',
        'FROM_EMAIL',
        'SMTP_SERVER',
        'SMTP_PORT'
    ]
    
    print("\n📧 Environment Variables:")
    for var in email_vars:
        value = os.getenv(var, 'NOT SET')
        print(f"   {var}: {value}")
    
    # Test the specific logic used in daily_inactive_monitor.py
    print("\n🎯 Testing daily_inactive_monitor.py email logic:")
    recipient_emails = os.getenv('RECIPIENT_EMAILS', '')
    recipients_list = [email.strip() for email in recipient_emails.split(',') if email.strip()]
    print(f"   RECIPIENT_EMAILS raw value: '{recipient_emails}'")
    print(f"   Parsed recipients list: {recipients_list}")
    print(f"   Number of recipients: {len(recipients_list)}")
    
    # Test the specific logic used in email_reporter.py 
    print("\n📮 Testing email_reporter.py email logic:")
    recipients_env = os.getenv('RECIPIENTS', '')
    recipients_list_old = [r.strip() for r in recipients_env.split(",")] if recipients_env else []
    print(f"   RECIPIENTS raw value: '{recipients_env}'")
    print(f"   Parsed recipients list: {recipients_list_old}")
    print(f"   Number of recipients: {len(recipients_list_old)}")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    debug_email_config()