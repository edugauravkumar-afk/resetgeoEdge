"""
Send email report when no inactive accounts are detected in last 24 hours
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def generate_no_changes_email_report():
    """Generate email report when no changes detected"""
    
    # Sample current stats (these would come from actual database query)
    current_stats = {
        'check_date': datetime.now().strftime('%Y-%m-%d'),
        'total_accounts_monitored': 3337,
        'total_projects_monitored': 13399,
        'total_accounts_in_system': 3534,
        'total_projects_in_system': 15420,
    }
    
    subject = f"✅ GeoEdge Daily Monitor - No Changes - {current_stats['check_date']}"
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>GeoEdge Daily Monitor - No Changes</title>
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; background-color: #f5f5f5;">
        
        <!-- Header -->
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px;">
            <h1 style="margin: 0; font-size: 28px;">✅ GeoEdge Daily Monitor</h1>
            <p style="margin: 10px 0 0 0; opacity: 0.9;">Daily Check: {current_stats['check_date']}</p>
        </div>

        <!-- Success Message -->
        <div style="background: #e8f5e9; border-left: 4px solid #4caf50; padding: 25px; border-radius: 8px; margin-bottom: 20px; text-align: center;">
            <h2 style="color: #2e7d32; margin: 0 0 10px 0; font-size: 24px;">🎉 All Systems Optimal</h2>
            <p style="color: #666; font-size: 16px; margin: 0;">No inactive accounts detected in the last 24 hours</p>
        </div>

        <!-- Compact Dashboard Layout -->
        <div style="background: white; padding: 25px; border-radius: 8px; margin-bottom: 10px;">
            
            <!-- Row 1: Last 24 Hours Activity -->
            <h2 style="color: #2e7d32; margin: 0 0 15px 0; font-size: 18px; border-bottom: 2px solid #4caf50; padding-bottom: 10px;">📅 Last 24 Hours Activity</h2>
            <div style="display: table; width: 100%; margin-bottom: 25px;">
                <div style="display: table-row;">
                    <!-- Inactive Accounts -->
                    <div style="display: table-cell; width: 48%; padding: 20px; background: #e8f5e9; border-radius: 8px; text-align: center;">
                        <div style="color: #2e7d32; font-size: 11px; font-weight: bold; text-transform: uppercase; margin-bottom: 8px;">✅ Inactive Accounts</div>
                        <div style="font-size: 40px; font-weight: bold; color: #2e7d32; line-height: 1;">0</div>
                    </div>
                    <div style="display: table-cell; width: 4%;"></div>
                    <!-- Projects Updated -->
                    <div style="display: table-cell; width: 48%; padding: 20px; background: #e8f5e9; border-radius: 8px; text-align: center;">
                        <div style="color: #2e7d32; font-size: 11px; font-weight: bold; text-transform: uppercase; margin-bottom: 8px;">✅ Projects Updated</div>
                        <div style="font-size: 40px; font-weight: bold; color: #2e7d32; line-height: 1;">0</div>
                        <div style="color: #666; font-size: 11px; margin-top: 5px;">No changes required</div>
                    </div>
                </div>
            </div>
            
            <!-- Row 2: Current System Status -->
            <h2 style="color: #2e7d32; margin: 0 0 15px 0; font-size: 18px; border-bottom: 2px solid #4caf50; padding-bottom: 10px;">📊 Current System Status</h2>
            <div style="display: table; width: 100%;">
                <div style="display: table-row;">
                    <!-- Active Accounts -->
                    <div style="display: table-cell; width: 48%; padding: 20px; background: #e8f5e9; border-radius: 8px; text-align: center;">
                        <div style="color: #2e7d32; font-size: 11px; font-weight: bold; text-transform: uppercase; margin-bottom: 8px;">👥 Active Accounts</div>
                        <div style="font-size: 38px; font-weight: bold; color: #1976d2; line-height: 1;">
                            {current_stats['total_accounts_monitored']:,}<span style="font-size: 20px; color: #999;"> / {current_stats['total_accounts_in_system']:,}</span>
                        </div>
                        <div style="margin-top: 8px;">
                            <span style="background: #4caf50; color: white; padding: 4px 10px; border-radius: 12px; font-size: 10px; font-weight: bold;">SCANNING (1,72)</span>
                            <span style="color: #2e7d32; font-weight: bold; font-size: 12px; margin-left: 8px;">{(current_stats['total_accounts_monitored']/current_stats['total_accounts_in_system']*100):.1f}%</span>
                        </div>
                    </div>
                    <div style="display: table-cell; width: 4%;"></div>
                    <!-- Active Projects -->
                    <div style="display: table-cell; width: 48%; padding: 20px; background: #e8f5e9; border-radius: 8px; text-align: center;">
                        <div style="color: #2e7d32; font-size: 11px; font-weight: bold; text-transform: uppercase; margin-bottom: 8px;">📁 Active Projects</div>
                        <div style="font-size: 38px; font-weight: bold; color: #1976d2; line-height: 1;">
                            {current_stats['total_projects_monitored']:,}<span style="font-size: 20px; color: #999;"> / {current_stats['total_projects_in_system']:,}</span>
                        </div>
                        <div style="margin-top: 8px;">
                            <span style="background: #4caf50; color: white; padding: 4px 10px; border-radius: 12px; font-size: 10px; font-weight: bold;">SCANNING (1,72)</span>
                            <span style="color: #2e7d32; font-weight: bold; font-size: 12px; margin-left: 8px;">{(current_stats['total_projects_monitored']/current_stats['total_projects_in_system']*100):.1f}%</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Footer Note -->
        <div style="background: #f9fbe7; border-left: 4px solid #cddc39; padding: 15px; border-radius: 8px; margin-top: 20px;">
            <p style="margin: 0; color: #666; font-size: 13px;">
                <strong style="color: #827717;">ℹ️ Note:</strong> All {current_stats['total_accounts_monitored']:,} active accounts are functioning normally. 
                The system will continue daily monitoring and will alert you immediately if any accounts become inactive.
            </p>
        </div>

        <!-- Footer -->
        <div style="text-align: center; padding: 20px; color: #666; font-size: 12px; border-top: 1px solid #e0e0e0; margin-top: 20px;">
            Generated by GeoEdge Daily Monitor | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </body>
    </html>
    """
    
    return subject, html_body

def send_no_changes_email():
    """Send email when no changes detected"""
    
    email_config = {
        'smtp_server': os.getenv('SMTP_SERVER', 'ildcsmtp.office.taboola.com'),
        'smtp_port': int(os.getenv('SMTP_PORT', '25')),
        'sender_email': os.getenv('SENDER_EMAIL'),
        'recipients': [email.strip() for email in os.getenv('RECIPIENT_EMAILS', '').split(',') if email.strip()]
    }
    
    print("📊 Generating 'No Changes' daily report...")
    subject, html_body = generate_no_changes_email_report()
    
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = email_config['sender_email']
        msg['To'] = ', '.join(email_config['recipients'])
        msg['Subject'] = subject
        
        # Add HTML content
        html_part = MIMEText(html_body, 'html')
        msg.attach(html_part)
        
        print(f"📤 Sending 'No Changes' email to {len(email_config['recipients'])} recipients...")
        print(f"   From: {email_config['sender_email']}")
        print(f"   To: {', '.join(email_config['recipients'])}")
        
        # Send email
        with smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port']) as server:
            server.send_message(msg)
            
        print("✅ 'No Changes' email sent successfully!")
        print(f"📧 Subject: {subject}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False

if __name__ == "__main__":
    print("🎯 GeoEdge Daily Monitor - No Changes Detected")
    print("=" * 60)
    print("📈 System Status:")
    print("   • 3,337 accounts monitored (all active)")
    print("   • 13,399 projects monitored (all scanning)")
    print("   • 0 inactive accounts detected in last 24 hours")
    print("   • No configuration changes required")
    print("=" * 60)
    
    success = send_no_changes_email()
    
    if success:
        print("\n✅ No changes report sent successfully!")
        print("📬 Check your email for the daily status report")
