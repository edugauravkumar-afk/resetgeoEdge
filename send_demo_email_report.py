#!/usr/bin/env python3
"""
Demo Email Report Generator
Sends a sample email report with mock data to demonstrate the format
"""

import os
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def generate_demo_email_report():
    """Generate a demo email report with sample data"""
    
    # Mock statistics (similar to what we'd get from real monitoring)
    demo_stats = {
        'run_timestamp': datetime.now().isoformat(),
        'total_configured_accounts': 3534,
        'total_projects_configured': 15420,
        'total_inactive_accounts': 197,
        'total_inactive_projects': 2021,
        'total_active_accounts': 3337,
        'total_active_projects': 13399,
        'new_inactive_accounts_24h': 5,
        'new_inactive_projects_24h': 23,
        'projects_reset_to_manual': 23,
        'reset_success_count': 23,
        'reset_failure_count': 0,
    }
    
    # Mock newly inactive accounts
    new_inactive_accounts = [1920001, 1920002, 1920003, 1920004, 1920005]
    projects_per_account = [5, 4, 6, 3, 5]
    
    subject = f"🔍 Daily GeoEdge Inactive Account Monitor - {datetime.now().strftime('%Y-%m-%d')} - 5 New Inactive Accounts Found!"
    
    # Calculate active accounts/projects
    active_accounts = demo_stats['total_configured_accounts'] - demo_stats['total_inactive_accounts']
    active_projects = demo_stats['total_projects_configured'] - demo_stats['total_inactive_projects']
    
    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .header {{ background-color: #f0f8ff; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
            .stats-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 20px 0; }}
            .stat-box {{ background-color: #f9f9f9; padding: 15px; border-radius: 8px; border-left: 4px solid #4CAF50; }}
            .alert-box {{ background-color: #fff3cd; padding: 15px; border-radius: 8px; border-left: 4px solid #ffc107; }}
            .success-box {{ background-color: #d4edda; padding: 15px; border-radius: 8px; border-left: 4px solid #28a745; }}
            .number {{ font-size: 24px; font-weight: bold; color: #2c3e50; }}
            .label {{ font-size: 14px; color: #7f8c8d; margin-top: 5px; }}
            table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            .highlight {{ background-color: #ffeb3b; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🔍 Daily GeoEdge Inactive Account Monitor</h1>
            <p><strong>Report Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>Monitoring Period:</strong> Last 24 hours</p>
            <p><strong>Status:</strong> 📧 Demo Report (Sample Data)</p>
        </div>
        
        <h2>📊 Overall System Statistics</h2>
        <div class="stats-grid">
            <div class="stat-box">
                <div class="number">{demo_stats['total_configured_accounts']:,}</div>
                <div class="label">Total Configured Accounts (X)</div>
            </div>
            <div class="stat-box">
                <div class="number">{demo_stats['total_projects_configured']:,}</div>
                <div class="label">Total Configured Projects (Y)</div>
            </div>
            <div class="stat-box">
                <div class="number">{demo_stats['total_inactive_accounts']:,}</div>
                <div class="label">Total Inactive Accounts (Z)</div>
            </div>
            <div class="stat-box">
                <div class="number">{demo_stats['total_inactive_projects']:,}</div>
                <div class="label">Total Projects with (0,0) Config (Z1)</div>
            </div>
            <div class="stat-box">
                <div class="number">{active_accounts:,}</div>
                <div class="label">Total Active Accounts (A)</div>
            </div>
            <div class="stat-box">
                <div class="number">{active_projects:,}</div>
                <div class="label">Total Projects with (1,72) Config (B)</div>
            </div>
        </div>
        
        <div class="alert-box">
            <h2>⚠️ New Inactive Accounts Detected (Last 24h)</h2>
            <div class="stats-grid">
                <div class="stat-box">
                    <div class="number highlight">{demo_stats['new_inactive_accounts_24h']:,}</div>
                    <div class="label">New Inactive Accounts Found (D)</div>
                </div>
                <div class="stat-box">
                    <div class="number highlight">{demo_stats['new_inactive_projects_24h']:,}</div>
                    <div class="label">Total Projects Found Under Inactive Accounts (F)</div>
                </div>
            </div>
            
            <h3>📋 New Inactive Accounts List:</h3>
            <table>
                <tr><th>Account ID</th><th>Projects Count</th><th>Status</th></tr>
    """
    
    for i, account_id in enumerate(new_inactive_accounts):
        html_body += f"<tr><td>{account_id}</td><td>{projects_per_account[i]}</td><td>Newly Inactive</td></tr>"
    
    html_body += f"""
            </table>
        </div>
        
        <div class="success-box">
            <h2>✅ Project Configuration Updates</h2>
            <div class="stats-grid">
                <div class="stat-box">
                    <div class="number">{demo_stats['projects_reset_to_manual']:,}</div>
                    <div class="label">Projects Reset to Manual Mode (0,0)</div>
                </div>
                <div class="stat-box">
                    <div class="number">{demo_stats['reset_success_count']:,}</div>
                    <div class="label">Successful Updates</div>
                </div>
            </div>
            <p><strong>All {demo_stats['new_inactive_projects_24h']} projects successfully updated from (1,72) → (0,0)</strong></p>
        </div>
        
        <h2>📈 Current System Status - Summary</h2>
        <div class="success-box">
            <h3>✅ Remaining Active System</h3>
            <div class="stats-grid">
                <div class="stat-box">
                    <div class="number">{active_accounts:,}</div>
                    <div class="label">Remaining Active Accounts</div>
                </div>
                <div class="stat-box">
                    <div class="number">{active_projects:,}</div>
                    <div class="label">Remaining Active Projects (1,72)</div>
                </div>
            </div>
            
            <h3>📊 Today's Activity Summary:</h3>
            <ul>
                <li><strong>Inactive accounts found in last 24hrs:</strong> {demo_stats['new_inactive_accounts_24h']} accounts</li>
                <li><strong>Total projects under these accounts:</strong> {demo_stats['new_inactive_projects_24h']} projects</li>
                <li><strong>Projects successfully updated to (0,0):</strong> {demo_stats['projects_reset_to_manual']}</li>
                <li><strong>Update success rate:</strong> 100% ({demo_stats['reset_success_count']}/{demo_stats['new_inactive_projects_24h']})</li>
                <li><strong>Remaining system load:</strong> {active_accounts:,} active accounts with {active_projects:,} scanning projects</li>
            </ul>
        </div>
        
        <hr>
        <p><small>Generated by GeoEdge Daily Monitor | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 📧 Demo Report</small></p>
    </body>
    </html>
    """
    
    return subject, html_body

def send_demo_email():
    """Send demo email report"""
    
    email_config = {
        'smtp_server': os.getenv('SMTP_SERVER', 'ildcsmtp.office.taboola.com'),
        'smtp_port': int(os.getenv('SMTP_PORT', '25')),
        'sender_email': os.getenv('SENDER_EMAIL'),
        'recipients': [email.strip() for email in os.getenv('RECIPIENT_EMAILS', '').split(',') if email.strip()]
    }
    
    print("📧 Generating demo email report...")
    subject, html_body = generate_demo_email_report()
    
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = email_config['sender_email']
        msg['To'] = ', '.join(email_config['recipients'])
        msg['Subject'] = subject
        
        # Add HTML content
        html_part = MIMEText(html_body, 'html')
        msg.attach(html_part)
        
        print(f"📤 Sending email to {len(email_config['recipients'])} recipients...")
        print(f"   From: {email_config['sender_email']}")
        print(f"   To: {', '.join(email_config['recipients'])}")
        
        # Send email
        with smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port']) as server:
            server.send_message(msg)
            
        print("✅ Demo email report sent successfully!")
        print(f"📧 Subject: {subject}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to send demo email: {e}")
        return False

if __name__ == "__main__":
    print("🎯 GeoEdge Daily Monitor - Demo Email Report")
    print("=" * 50)
    
    success = send_demo_email()
    
    if success:
        print("\n✅ Demo completed successfully!")
        print("📬 Check your email for the sample daily report")
    else:
        print("\n❌ Demo failed - please check email configuration")