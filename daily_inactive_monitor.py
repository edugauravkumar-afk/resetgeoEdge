#!/usr/bin/env python3
"""
Daily Inactive Account Monitor
Checks for newly inactive accounts, resets their projects to Manual Mode,
and sends comprehensive email reports.
"""

import os
import sys
import json
import smtplib
import pymysql
import requests
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import time
import logging

# Load environment variables
load_dotenv()

# Configure logging
log_filename = f"daily_monitor_{datetime.now().strftime('%Y%m%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DailyInactiveMonitor:
    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST'),
            'port': int(os.getenv('DB_PORT', 6033)),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'database': os.getenv('DB_NAME'),
            'charset': 'utf8mb4',
            'client_flag': pymysql.constants.CLIENT.PLUGIN_AUTH
        }
        
        self.geoedge_config = {
            'api_key': os.getenv('GEOEDGE_API_KEY'),
            'base_url': os.getenv('GEOEDGE_API_BASE', 'https://api.geoedge.com/rest/analytics/v3')
        }
        
        self.email_config = {
            'smtp_server': os.getenv('SMTP_SERVER', 'ildcsmtp.office.taboola.com'),
            'smtp_port': int(os.getenv('SMTP_PORT', '25')),
            'sender_email': os.getenv('SENDER_EMAIL'),
            'recipients': [email.strip() for email in os.getenv('RECIPIENT_EMAILS', '').split(',') if email.strip()]
        }
        
        # File to track previous state
        self.state_file = 'daily_monitor_state.json'
        
        # Statistics container
        self.stats = {
            'run_timestamp': datetime.now().isoformat(),
            'total_configured_accounts': 0,
            'total_projects_configured': 0,
            'total_inactive_accounts': 0,
            'total_inactive_projects': 0,
            'total_active_accounts': 0,
            'total_active_projects': 0,
            'new_inactive_accounts_24h': 0,
            'new_inactive_projects_24h': 0,
            'projects_reset_to_manual': 0,
            'reset_success_count': 0,
            'reset_failure_count': 0,
            'remaining_active_accounts': 0,
            'remaining_active_projects': 0
        }

    def load_previous_state(self):
        """Load previous monitoring state"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            return {'inactive_accounts': [], 'last_check': None}
        except Exception as e:
            logger.error(f"Error loading previous state: {e}")
            return {'inactive_accounts': [], 'last_check': None}

    def save_current_state(self, inactive_accounts):
        """Save current monitoring state"""
        try:
            state = {
                'inactive_accounts': list(inactive_accounts),
                'last_check': datetime.now().isoformat(),
                'stats': self.stats
            }
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving current state: {e}")

    def get_database_connection(self):
        """Create database connection"""
        try:
            return pymysql.connect(**self.db_config)
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            sys.exit(1)

    def get_all_configured_accounts(self):
        """Get all accounts with Auto Mode projects (1,72)"""
        query = """
        SELECT DISTINCT account_id,
               COUNT(*) as project_count
        FROM project_config 
        WHERE auto_scan = 1 AND times_per_day = 72
        GROUP BY account_id
        ORDER BY account_id
        """
        
        try:
            conn = self.get_database_connection()
            with conn.cursor() as cursor:
                cursor.execute(query)
                results = cursor.fetchall()
                
                accounts = {}
                total_projects = 0
                for account_id, project_count in results:
                    accounts[account_id] = project_count
                    total_projects += project_count
                
                self.stats['total_configured_accounts'] = len(accounts)
                self.stats['total_projects_configured'] = total_projects
                
                return accounts
        finally:
            conn.close()

    def check_account_activity(self, account_ids):
        """Check which accounts have been inactive (no alerts in 30+ days)"""
        if not account_ids:
            return set(), set()
        
        # Convert to list for SQL IN clause
        account_list = list(account_ids)
        placeholders = ','.join(['%s'] * len(account_list))
        
        query = f"""
        SELECT DISTINCT account_id
        FROM alerts_raw 
        WHERE account_id IN ({placeholders})
        AND created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        """
        
        try:
            conn = self.get_database_connection()
            with conn.cursor() as cursor:
                cursor.execute(query, account_list)
                active_account_results = cursor.fetchall()
                
                # Extract active account IDs
                active_accounts = {row[0] for row in active_account_results}
                inactive_accounts = set(account_ids) - active_accounts
                
                return active_accounts, inactive_accounts
                
        except Exception as e:
            logger.error(f"Error checking account activity: {e}")
            return set(), set()
        finally:
            conn.close()

    def get_projects_for_accounts(self, account_ids):
        """Get all projects for specified accounts"""
        if not account_ids:
            return {}
        
        account_list = list(account_ids)
        placeholders = ','.join(['%s'] * len(account_list))
        
        query = f"""
        SELECT account_id, project_id
        FROM project_config 
        WHERE account_id IN ({placeholders})
        AND auto_scan = 1 AND times_per_day = 72
        ORDER BY account_id, project_id
        """
        
        try:
            conn = self.get_database_connection()
            with conn.cursor() as cursor:
                cursor.execute(query, account_list)
                results = cursor.fetchall()
                
                projects_by_account = {}
                for account_id, project_id in results:
                    if account_id not in projects_by_account:
                        projects_by_account[account_id] = []
                    projects_by_account[account_id].append(project_id)
                
                return projects_by_account
                
        except Exception as e:
            logger.error(f"Error getting projects for accounts: {e}")
            return {}
        finally:
            conn.close()

    def update_project_to_manual_mode(self, project_id):
        """Update a single project to Manual Mode via GeoEdge API"""
        url = f"{self.geoedge_config['base_url']}/projects/{project_id}/config"
        
        # Fixed payload - only auto_scan parameter (no times_per_day when auto_scan=0)
        data = {
            'auto_scan': '0'
        }
        
        headers = {
            'Authorization': f"Bearer {self.geoedge_config['api_key']}",
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        try:
            response = requests.put(url, data=data, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('response', {}).get('status') == 'Success':
                    return True, "Success"
                else:
                    return False, f"API returned non-success status: {result}"
            else:
                return False, f"HTTP {response.status_code}: {response.text}"
                
        except Exception as e:
            return False, f"Request failed: {str(e)}"

    def reset_projects_to_manual(self, projects_by_account):
        """Reset all projects to Manual Mode"""
        reset_results = {
            'success': [],
            'failures': []
        }
        
        total_projects = sum(len(projects) for projects in projects_by_account.values())
        processed = 0
        
        logger.info(f"Starting to reset {total_projects} projects to Manual Mode...")
        
        for account_id, project_ids in projects_by_account.items():
            logger.info(f"Processing {len(project_ids)} projects for account {account_id}")
            
            for project_id in project_ids:
                processed += 1
                
                success, message = self.update_project_to_manual_mode(project_id)
                
                if success:
                    reset_results['success'].append({
                        'account_id': account_id,
                        'project_id': project_id
                    })
                    logger.info(f"[{processed}/{total_projects}] ✅ {project_id} (Account: {account_id}) → Manual Mode")
                else:
                    reset_results['failures'].append({
                        'account_id': account_id,
                        'project_id': project_id,
                        'error': message
                    })
                    logger.error(f"[{processed}/{total_projects}] ❌ {project_id} (Account: {account_id}) → FAILED: {message}")
                
                # Rate limiting
                time.sleep(2)
                
                if processed % 50 == 0:
                    logger.info(f"Progress: {processed}/{total_projects} ({100*processed/total_projects:.1f}%)")
        
        self.stats['reset_success_count'] = len(reset_results['success'])
        self.stats['reset_failure_count'] = len(reset_results['failures'])
        self.stats['projects_reset_to_manual'] = len(reset_results['success'])
        
        return reset_results

    def generate_email_report(self, previous_state, current_inactive, new_inactive, projects_by_account, reset_results):
        """Generate comprehensive email report with compact design"""
        
        # Determine if changes were made
        has_changes = len(new_inactive) > 0
        
        if has_changes:
            subject = f"⚠️ GeoEdge Daily Monitor - {len(new_inactive)} Inactive Accounts - {datetime.now().strftime('%Y-%m-%d')}"
        else:
            subject = f"✅ GeoEdge Daily Monitor - No Changes - {datetime.now().strftime('%Y-%m-%d')}"
        
        # Calculate current active counts
        active_accounts = self.stats['total_configured_accounts'] - self.stats['total_inactive_accounts']
        active_projects = self.stats['total_projects_configured'] - self.stats['total_inactive_projects']
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>GeoEdge Daily Monitor</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; background-color: #f5f5f5;">
            
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px;">
                <h1 style="margin: 0; font-size: 28px;">{"⚠️" if has_changes else "✅"} GeoEdge Daily Monitor</h1>
                <p style="margin: 10px 0 0 0; opacity: 0.9;">Daily Check: {datetime.now().strftime('%Y-%m-%d')}</p>
            </div>
        """
        
        # Success or Alert message
        if not has_changes:
            html_body += """
            <!-- Success Message -->
            <div style="background: #e8f5e9; border-left: 4px solid #4caf50; padding: 25px; border-radius: 8px; margin-bottom: 20px; text-align: center;">
                <h2 style="color: #2e7d32; margin: 0 0 10px 0; font-size: 24px;">🎉 All Systems Optimal</h2>
                <p style="color: #666; font-size: 16px; margin: 0;">No inactive accounts detected in the last 24 hours</p>
            </div>
            """
        
        html_body += f"""
            <!-- Compact Dashboard Layout -->
            <div style="background: white; padding: 25px; border-radius: 8px; margin-bottom: 10px;">
                
                <!-- Row 1: Last 24 Hours Activity -->
                <h2 style="color: {"#e65100" if has_changes else "#2e7d32"}; margin: 0 0 15px 0; font-size: 18px; border-bottom: 2px solid {"#ff9800" if has_changes else "#4caf50"}; padding-bottom: 10px;">📅 Last 24 Hours Activity</h2>
                <div style="display: table; width: 100%; margin-bottom: 25px;">
                    <div style="display: table-row;">
                        <!-- Inactive Accounts -->
                        <div style="display: table-cell; width: 48%; padding: 20px; background: {"#fff3e0" if has_changes else "#e8f5e9"}; border-radius: 8px; text-align: center;">
                            <div style="color: {"#e65100" if has_changes else "#2e7d32"}; font-size: 11px; font-weight: bold; text-transform: uppercase; margin-bottom: 8px;">{"⚠️" if has_changes else "✅"} Inactive Accounts</div>
                            <div style="font-size: 40px; font-weight: bold; color: {"#e65100" if has_changes else "#2e7d32"}; line-height: 1;">{len(new_inactive)}</div>
                        </div>
                        <div style="display: table-cell; width: 4%;"></div>
                        <!-- Projects Updated -->
                        <div style="display: table-cell; width: 48%; padding: 20px; background: {"#ffebee" if has_changes else "#e8f5e9"}; border-radius: 8px; text-align: center;">
                            <div style="color: {"#d32f2f" if has_changes else "#2e7d32"}; font-size: 11px; font-weight: bold; text-transform: uppercase; margin-bottom: 8px;">{"🔧" if has_changes else "✅"} Projects Updated</div>
                            <div style="font-size: 40px; font-weight: bold; color: {"#d32f2f" if has_changes else "#2e7d32"}; line-height: 1;">{self.stats['projects_reset_to_manual']:,}</div>
                            <div style="color: #666; font-size: 11px; margin-top: 5px;">{"(1,72) → (0,0)" if has_changes else "No changes required"}</div>
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
                                {active_accounts:,}<span style="font-size: 20px; color: #999;"> / {self.stats['total_configured_accounts']:,}</span>
                            </div>
                            <div style="margin-top: 8px;">
                                <span style="background: #4caf50; color: white; padding: 4px 10px; border-radius: 12px; font-size: 10px; font-weight: bold;">SCANNING (1,72)</span>
                                <span style="color: #2e7d32; font-weight: bold; font-size: 12px; margin-left: 8px;">{(active_accounts/self.stats['total_configured_accounts']*100):.1f}%</span>
                            </div>
                        </div>
                        <div style="display: table-cell; width: 4%;"></div>
                        <!-- Active Projects -->
                        <div style="display: table-cell; width: 48%; padding: 20px; background: #e8f5e9; border-radius: 8px; text-align: center;">
                            <div style="color: #2e7d32; font-size: 11px; font-weight: bold; text-transform: uppercase; margin-bottom: 8px;">📁 Active Projects</div>
                            <div style="font-size: 38px; font-weight: bold; color: #1976d2; line-height: 1;">
                                {active_projects:,}<span style="font-size: 20px; color: #999;"> / {self.stats['total_projects_configured']:,}</span>
                            </div>
                            <div style="margin-top: 8px;">
                                <span style="background: #4caf50; color: white; padding: 4px 10px; border-radius: 12px; font-size: 10px; font-weight: bold;">SCANNING (1,72)</span>
                                <span style="color: #2e7d32; font-weight: bold; font-size: 12px; margin-left: 8px;">{(active_projects/self.stats['total_projects_configured']*100):.1f}%</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        """
        
        # Add details for accounts that were found inactive
        if has_changes and new_inactive:
            html_body += f"""
            <!-- Detailed Account List -->
            <div style="background: white; padding: 25px; border-radius: 8px; margin-top: 20px;">
                <h2 style="color: #d32f2f; margin-top: 0; font-size: 18px; border-bottom: 2px solid #f44336; padding-bottom: 10px;">📋 Inactive Account Details</h2>
                <table style="width: 100%; border-collapse: collapse; background: #f9f9f9;">
                    <tr style="background: #f5f5f5;">
                        <th style="padding: 10px; text-align: left; border: 1px solid #ddd; font-size: 12px;">Account ID</th>
                        <th style="padding: 10px; text-align: center; border: 1px solid #ddd; font-size: 12px;">Projects</th>
                        <th style="padding: 10px; text-align: center; border: 1px solid #ddd; font-size: 12px;">Status</th>
                    </tr>
            """
            
            for account_id in sorted(new_inactive):
                project_count = len(projects_by_account.get(account_id, []))
                html_body += f"""
                    <tr>
                        <td style="padding: 10px; border: 1px solid #ddd; font-size: 13px;">{account_id}</td>
                        <td style="padding: 10px; text-align: center; border: 1px solid #ddd; font-size: 13px;">{project_count}</td>
                        <td style="padding: 10px; text-align: center; border: 1px solid #ddd; font-size: 13px;">✅ Reset to Manual</td>
                    </tr>
                """
            
            html_body += """
                </table>
            </div>
            """
        
        # Footer note
        if not has_changes:
            html_body += f"""
            <!-- Footer Note -->
            <div style="background: #f9fbe7; border-left: 4px solid #cddc39; padding: 15px; border-radius: 8px; margin-top: 20px;">
                <p style="margin: 0; color: #666; font-size: 13px;">
                    <strong style="color: #827717;">ℹ️ Note:</strong> All {active_accounts:,} active accounts are functioning normally. 
                    The system will continue daily monitoring and will alert you immediately if any accounts become inactive.
                </p>
            </div>
            """
        
        html_body += f"""
            <!-- Footer -->
            <div style="text-align: center; padding: 20px; color: #666; font-size: 12px; border-top: 1px solid #e0e0e0; margin-top: 20px;">
                Generated by GeoEdge Daily Monitor | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </div>
        </body>
        </html>
        """
        
        return subject, html_body

    def send_email_alert(self, subject, html_body):
        """Send email alert"""
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = self.email_config['sender_email']
            msg['To'] = ', '.join(self.email_config['recipients'])
            msg['Subject'] = subject
            
            # Add HTML content
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)
            
            # Send email (Taboola SMTP doesn't require authentication)
            with smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port']) as server:
                server.send_message(msg)
                
            logger.info(f"Email alert sent successfully to {len(self.email_config['recipients'])} recipients")
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")

    def run_daily_check(self):
        """Main execution function"""
        logger.info("Starting daily inactive account monitoring...")
        
        try:
            # Load previous state
            previous_state = self.load_previous_state()
            previous_inactive = set(previous_state.get('inactive_accounts', []))
            
            # Get all configured accounts
            logger.info("Fetching all configured accounts...")
            configured_accounts = self.get_all_configured_accounts()
            
            if not configured_accounts:
                logger.error("No configured accounts found!")
                return
            
            logger.info(f"Found {len(configured_accounts)} configured accounts with {self.stats['total_projects_configured']} projects")
            
            # Check account activity
            logger.info("Checking account activity...")
            active_accounts, inactive_accounts = self.check_account_activity(configured_accounts.keys())
            
            # Update statistics
            self.stats['total_inactive_accounts'] = len(inactive_accounts)
            self.stats['total_active_accounts'] = len(active_accounts)
            
            # Calculate project counts
            self.stats['total_inactive_projects'] = sum(
                configured_accounts[acc_id] for acc_id in inactive_accounts
            )
            self.stats['total_active_projects'] = sum(
                configured_accounts[acc_id] for acc_id in active_accounts
            )
            
            # Find newly inactive accounts
            new_inactive = inactive_accounts - previous_inactive
            self.stats['new_inactive_accounts_24h'] = len(new_inactive)
            
            logger.info(f"Account Status: {len(active_accounts)} active, {len(inactive_accounts)} inactive")
            
            if new_inactive:
                logger.info(f"🚨 Found {len(new_inactive)} newly inactive accounts: {list(new_inactive)}")
                
                # Get projects for newly inactive accounts
                projects_by_account = self.get_projects_for_accounts(new_inactive)
                self.stats['new_inactive_projects_24h'] = sum(len(projects) for projects in projects_by_account.values())
                
                logger.info(f"Found {self.stats['new_inactive_projects_24h']} projects to reset to Manual Mode")
                
                # Reset projects to Manual Mode
                if projects_by_account:
                    reset_results = self.reset_projects_to_manual(projects_by_account)
                    logger.info(f"Reset Results: {self.stats['reset_success_count']} success, {self.stats['reset_failure_count']} failures")
                else:
                    reset_results = {'success': [], 'failures': []}
            else:
                logger.info("✅ No newly inactive accounts found")
                projects_by_account = {}
                reset_results = {'success': [], 'failures': []}
            
            # Generate and send email report
            logger.info("Generating email report...")
            subject, html_body = self.generate_email_report(
                previous_state, inactive_accounts, new_inactive, 
                projects_by_account, reset_results
            )
            
            self.send_email_alert(subject, html_body)
            
            # Save current state
            self.save_current_state(inactive_accounts)
            
            logger.info("Daily monitoring completed successfully!")
            
            return {
                'success': True,
                'new_inactive_accounts': len(new_inactive),
                'projects_reset': self.stats['projects_reset_to_manual'],
                'stats': self.stats
            }
            
        except Exception as e:
            logger.error(f"Daily monitoring failed: {e}")
            
            # Send error alert
            error_subject = f"❌ GeoEdge Daily Monitor Error - {datetime.now().strftime('%Y-%m-%d')}"
            error_body = f"""
            <html>
            <body>
                <h1>❌ Daily Monitor Error</h1>
                <p><strong>Time:</strong> {datetime.now().isoformat()}</p>
                <p><strong>Error:</strong> {str(e)}</p>
                <p>Please check the logs and system status.</p>
            </body>
            </html>
            """
            
            try:
                self.send_email_alert(error_subject, error_body)
            except:
                pass  # Don't fail if email also fails
            
            return {'success': False, 'error': str(e)}

if __name__ == "__main__":
    monitor = DailyInactiveMonitor()
    result = monitor.run_daily_check()
    
    if result['success']:
        print(f"✅ Daily monitoring completed successfully!")
        print(f"📊 New inactive accounts: {result['new_inactive_accounts']}")
        print(f"🔄 Projects reset: {result['projects_reset']}")
    else:
        print(f"❌ Daily monitoring failed: {result['error']}")
        sys.exit(1)