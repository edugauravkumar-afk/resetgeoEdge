#!/usr/bin/env python3
"""
Email Module for GeoEdge Daily Reset Reports

Integrates the reusable email system with GeoEdge project management.
Sends daily reports with account status, project configurations, and any changes made.
"""

import os
import io
import csv
import smtplib
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class EmailSender:
    """Email sender class for sending HTML emails with CSV attachments."""
    
    def __init__(self, 
                 smtp_server: Optional[str] = None,
                 smtp_port: Optional[int] = None,
                 smtp_user: Optional[str] = None,
                 smtp_password: Optional[str] = None,
                 from_email: Optional[str] = None):
        """Initialize EmailSender with SMTP configuration."""
        self.smtp_server = smtp_server or self._env_or_fail("SMTP_SERVER")
        self.smtp_port = smtp_port or int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = smtp_user or os.getenv("SMTP_USER")
        self.smtp_password = smtp_password or os.getenv("SMTP_PASSWORD")
        self.from_email = from_email or self._env_or_fail("FROM_EMAIL")
        
    def _env_or_fail(self, key: str) -> str:
        """Get environment variable or raise error"""
        value = os.getenv(key, "").strip()
        if not value:
            raise RuntimeError(f"Missing environment variable: {key}")
        return value
    
    def log_message(self, message: str) -> None:
        """Log message to console with timestamp"""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")
    
    def send_email(self, 
                   subject: str,
                   html_content: str,
                   recipients: Optional[List[str]] = None,
                   cc_recipients: Optional[List[str]] = None,
                   csv_data: Optional[List[Dict[str, Any]]] = None,
                   csv_filename: Optional[str] = None) -> bool:
        """Send an HTML email with optional CSV attachment."""
        
        try:
            # Get recipients from environment if not provided
            if recipients is None:
                env_recipients = os.getenv("RECIPIENTS", "").strip()
                if not env_recipients:
                    raise RuntimeError("No recipients provided and RECIPIENTS env var not set")
                recipients = [r.strip() for r in env_recipients.split(",")]
            
            if cc_recipients is None:
                env_cc = os.getenv("CC_RECIPIENTS", "").strip()
                cc_recipients = [r.strip() for r in env_cc.split(",")] if env_cc else []
            
            # Create message
            msg = MIMEMultipart("alternative")
            msg["From"] = self.from_email
            msg["To"] = ", ".join(recipients)
            if cc_recipients:
                msg["Cc"] = ", ".join(cc_recipients)
            msg["Subject"] = subject
            
            # Attach HTML content
            html_part = MIMEText(html_content, "html")
            msg.attach(html_part)
            
            # Attach CSV if data provided
            if csv_data and csv_filename:
                csv_content = self._generate_csv_content(csv_data)
                csv_part = MIMEApplication(csv_content.encode("utf-8"), _subtype="csv")
                csv_part.add_header("Content-Disposition", "attachment", filename=csv_filename)
                msg.attach(csv_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                # Use STARTTLS for port 587
                if self.smtp_port == 587:
                    server.starttls()
                
                # Login if credentials provided
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                
                all_recipients = recipients + cc_recipients
                text = msg.as_string()
                server.sendmail(self.smtp_user or self.from_email, all_recipients, text)
            
            self.log_message(f"✅ Email sent successfully to {len(recipients)} recipients")
            return True
            
        except Exception as e:
            self.log_message(f"❌ Failed to send email: {str(e)}")
            return False
    
    def _generate_csv_content(self, data: List[Dict[str, Any]]) -> str:
        """Generate CSV content from list of dictionaries"""
        if not data:
            return ""
        
        headers = list(data[0].keys())
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)
        content = buffer.getvalue()
        buffer.close()
        return content


class HTMLEmailBuilder:
    """Helper class for building HTML email content with GeoEdge styling."""
    
    @staticmethod
    def build_geoedge_email(title: str, 
                           greeting: str = "Hi team,",
                           main_content: str = "",
                           footer_text: Optional[str] = None) -> str:
        """Build a GeoEdge-branded HTML email template."""
        if footer_text is None:
            footer_text = f"Generated by GeoEdge Reset Automation at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
        
        return f"""
        <html>
        <body>
            <div style="font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #1a73e8; border-bottom: 3px solid #1a73e8; padding-bottom: 10px; margin-bottom: 20px;">
                    🔧 {title}
                </h2>
                
                <p style="font-size: 14px; color: #444;">{greeting}</p>
                
                {main_content}
                
                <p style="color: #666; font-size: 12px; margin-top: 30px; border-top: 1px solid #eee; padding-top: 15px;">
                    {footer_text}
                </p>
            </div>
        </body>
        </html>
        """
    
    @staticmethod
    def build_success_message(message: str, details: Optional[str] = None) -> str:
        """Build a success message HTML block"""
        details_html = f"<p style=\"margin: 10px 0 0 0; font-size: 13px; color: #2d5a2d;\">{details}</p>" if details else ""
        
        return f"""
        <div style="background-color: #e8f5e8; border-left: 4px solid #4caf50; padding: 15px; margin: 20px 0; border-radius: 4px;">
            <p style="margin: 0; font-size: 15px; color: #2d5a2d; font-weight: bold;">
                ✅ {message}
            </p>
            {details_html}
        </div>
        """
    
    @staticmethod
    def build_info_message(message: str, details: Optional[str] = None) -> str:
        """Build an info message HTML block"""
        details_html = f"<p style=\"margin: 10px 0 0 0; font-size: 13px; color: #1565c0;\">{details}</p>" if details else ""
        
        return f"""
        <div style="background-color: #e3f2fd; border-left: 4px solid #2196f3; padding: 15px; margin: 20px 0; border-radius: 4px;">
            <p style="margin: 0; font-size: 15px; color: #1565c0; font-weight: bold;">
                ℹ️ {message}
            </p>
            {details_html}
        </div>
        """
    
    @staticmethod
    def build_summary_stats(stats: Dict[str, Any]) -> str:
        """Build a summary statistics box"""
        stats_html = ""
        for key, value in stats.items():
            stats_html += f"""
            <div style="display: inline-block; background: #f8f9fa; padding: 10px 15px; margin: 5px; border-radius: 6px; border-left: 3px solid #1a73e8;">
                <div style="font-size: 11px; color: #666; text-transform: uppercase;">{key}</div>
                <div style="font-size: 18px; font-weight: bold; color: #333;">{value}</div>
            </div>
            """
        
        return f"""
        <div style="background-color: #ffffff; border: 1px solid #e0e0e0; padding: 20px; margin: 20px 0; border-radius: 8px;">
            <h3 style="margin: 0 0 15px 0; color: #333; font-size: 16px;">📊 Summary Statistics</h3>
            <div style="text-align: center;">
                {stats_html}
            </div>
        </div>
        """
    
    @staticmethod
    def build_account_table(accounts: List[Dict[str, Any]], title: str = "Account Details", is_priority: bool = False) -> str:
        """Build a styled table for account information with scan configuration details"""
        if not accounts:
            return f"<p><em>No {title.lower()} to display.</em></p>"
        
        # Use red background for priority accounts
        header_bg_color = "#d32f2f" if is_priority else "#1a73e8"
        
        header_cells = f"""
        <th style="padding: 12px; border: 1px solid #ddd; background-color: {header_bg_color}; color: white; font-size: 13px;">Account ID</th>
        <th style="padding: 12px; border: 1px solid #ddd; background-color: {header_bg_color}; color: white; font-size: 13px;">Account Name</th>
        <th style="padding: 12px; border: 1px solid #ddd; background-color: {header_bg_color}; color: white; font-size: 13px;">Status</th>
        <th style="padding: 12px; border: 1px solid #ddd; background-color: {header_bg_color}; color: white; font-size: 13px;">Total Projects</th>
        <th style="padding: 12px; border: 1px solid #ddd; background-color: {header_bg_color}; color: white; font-size: 13px;">Auto Scan</th>
        <th style="padding: 12px; border: 1px solid #ddd; background-color: {header_bg_color}; color: white; font-size: 13px;">Scans Per Day</th>
        <th style="padding: 12px; border: 1px solid #ddd; background-color: #1a73e8; color: white; font-size: 13px;">Configuration</th>
        <th style="padding: 12px; border: 1px solid #ddd; background-color: #1a73e8; color: white; font-size: 13px;">Projects Reset</th>
        """
        
        rows = ""
        for account in accounts:
            # Handle different status types with appropriate colors
            status = account.get("status", "UNKNOWN")
            if "PRIORITY" in status:
                status_color = "#d32f2f"  # Red for priority
                row_bg = "#ffebee"  # Light red background
            elif status == "ACTIVE_AUTO_SCAN" or account.get("auto_scan", 0) == 1:
                status_color = "#ff9800"  # Orange for active
                row_bg = "#fff8e1"  # Light orange background
            else:
                status_color = "#4caf50"  # Green for inactive/reset
                row_bg = "#f1f8e9"  # Light green background
                
            # Get scan configuration
            auto_scan = account.get("auto_scan", 0)
            scans_per_day = account.get("scans_per_day", 0)
            total_projects = account.get("total_projects", 0)
            account_name = account.get("account_name", "N/A")
            
            # Configuration status
            if auto_scan == 0 and scans_per_day == 0:
                config_status = "Manual (0,0)"
                config_color = "#4caf50"  # Green for correct
                config_icon = "✅"
            elif auto_scan == 1 and scans_per_day == 72:
                config_status = "Auto (1,72)"
                config_color = "#ff9800"  # Orange for needs change
                config_icon = "⚠️"
            else:
                config_status = f"Custom ({auto_scan},{scans_per_day})"
                config_color = "#2196f3"  # Blue for other
                config_icon = "ℹ️"
            
            rows += f"""
            <tr style="background-color: {row_bg};">
                <td style="padding: 10px; border: 1px solid #ddd; font-family: monospace;">{account.get('account_id', 'N/A')}</td>
                <td style="padding: 10px; border: 1px solid #ddd; font-size: 12px;">{account_name}</td>
                <td style="padding: 10px; border: 1px solid #ddd;">
                    <span style="background: {status_color}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">
                        {status.replace('_', ' ')}
                    </span>
                </td>
                <td style="padding: 10px; border: 1px solid #ddd; text-align: center; font-weight: bold;">{total_projects}</td>
                <td style="padding: 10px; border: 1px solid #ddd; text-align: center; font-family: monospace;">{auto_scan}</td>
                <td style="padding: 10px; border: 1px solid #ddd; text-align: center; font-family: monospace;">{scans_per_day}</td>
                <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">
                    <span style="color: {config_color}; font-weight: bold; font-size: 12px;">
                        {config_icon} {config_status}
                    </span>
                </td>
                <td style="padding: 8px; border: 1px solid #ddd; font-size: 13px; text-align: center; font-weight: bold;">{account.get('projects_reset', account.get('total_projects', 0))}</td>
            </tr>
            """
        
        return f"""
        <div style="margin: 20px 0;">
            <h3 style="color: #333; margin-bottom: 10px; font-size: 16px;">{title}</h3>
            <div style="background: #f8f9fa; padding: 10px; border-radius: 4px; margin-bottom: 10px; font-size: 12px;">
                <strong>Configuration Guide:</strong>
                <span style="color: #4caf50;">✅ Manual (0,0)</span> = Auto-scan OFF, No daily scans (Recommended for inactive accounts) | 
                <span style="color: #ff9800;">⚠️ Auto (1,72)</span> = Auto-scan ON, 72 scans per day (Active accounts only)
            </div>
            <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                <thead>
                    <tr>{header_cells}</tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </div>
        """


class GeoEdgeEmailReporter:
    """Specialized email reporter for GeoEdge reset operations."""
    
    def __init__(self):
        self.sender = EmailSender()
        self.builder = HTMLEmailBuilder()
    
    def send_daily_reset_report(self, report_data: Dict[str, Any]) -> bool:
        """
        Send comprehensive daily reset report email for both Auto Mode (1,72) and APcampaign (1,12) monitoring.
        
        Args:
            report_data: Dictionary containing both monitoring results:
                - Auto Mode (1,72) monitoring data
                - APcampaign (1,12) monitoring data
                - Combined statistics
        """
        
        try:
            # Extract both monitoring results
            status = report_data.get("status", "success")
            
            # Auto Mode (1,72) data
            auto_mode_accounts_monitored = report_data.get("auto_mode_accounts_monitored", 0)
            auto_mode_projects_reset = report_data.get("total_projects_reset", 0)
            auto_mode_inactive = report_data.get("newly_inactive_count", 0)
            accounts_reset = report_data.get("accounts_reset", [])
            
            # APcampaign (1,12) data
            apcampaign_projects_monitored = report_data.get("apcampaign_projects_monitored", 0)
            apcampaign_projects_reset = report_data.get("apcampaign_projects_reset", 0)
            apcampaign_inactive = report_data.get("apcampaign_newly_inactive_count", 0)
            apcampaign_accounts_reset = report_data.get("apcampaign_accounts_reset", [])
            apcampaign_reset_success = report_data.get("apcampaign_reset_success", 0)
            apcampaign_reset_failures = report_data.get("apcampaign_reset_failures", 0)

            # APNews account status data (24h)
            apnews_accounts_monitored = report_data.get("apnews_accounts_monitored", 0)
            apnews_inactive_count = report_data.get("apnews_inactive_count", 0)
            apnews_newly_inactive_count = report_data.get("apnews_newly_inactive_count", 0)
            apnews_newly_inactive_accounts = report_data.get("apnews_newly_inactive_accounts", [])
            apnews_unknown_count = report_data.get("apnews_unknown_count", 0)
            
            # Non-matching projects reset data (Phase 4)
            non_matching_checked = report_data.get("non_matching_checked", 0)
            non_matching_reset = report_data.get("non_matching_reset", 0)
            non_matching_already_manual = report_data.get("non_matching_already_manual", 0)
            non_matching_errors = report_data.get("non_matching_errors", 0)
            non_matching_reset_details = report_data.get("non_matching_reset_details", [])
            
            # Combined totals
            total_accounts_monitored = report_data.get("total_accounts_monitored", auto_mode_accounts_monitored + apcampaign_projects_monitored)
            total_inactive_found = report_data.get("total_inactive_found", auto_mode_inactive + apcampaign_inactive)
            total_all_projects_reset = report_data.get("total_all_projects_reset", auto_mode_projects_reset + apcampaign_projects_reset + non_matching_reset)
            
            # Build enhanced summary statistics
            recent_auto_accounts = self._filter_recent_changes(accounts_reset)
            
            stats = {
                "Auto Mode (1,72) Accounts Monitored": f"{auto_mode_accounts_monitored:,}",
                "APcampaign Projects Monitored": f"{apcampaign_projects_monitored:,}",
                "APNews Accounts Monitored": f"{apnews_accounts_monitored:,}",
                "Auto Mode Became Inactive (24h)": auto_mode_inactive,
                "APcampaign Became Inactive": apcampaign_inactive,
                "APNews Became Inactive (24h)": apnews_newly_inactive_count,
                "Auto Mode Projects Reset": auto_mode_projects_reset,
                "APcampaign Projects Reset": apcampaign_projects_reset,
                "Non-Matching Projects Checked": f"{non_matching_checked:,}",
                "Non-Matching Projects Reset": non_matching_reset,
                "APNews Unknown": apnews_unknown_count,
                "Total Changes Made": "Yes" if total_all_projects_reset > 0 else "No",
                "Execution Time": f"{report_data.get('execution_time', 5.0):.1f}s"
            }
            
            # Build main content
            content_parts = []
            
            # Add header explaining dual monitoring
            content_parts.append("""
            <div style="background-color: #f3e5f5; border: 1px solid #9c27b0; padding: 15px; margin: 20px 0; border-radius: 6px;">
                <h4 style="margin: 0 0 10px 0; color: #6a1b9a;">🔍 Comprehensive GeoEdge Monitoring</h4>
                <div style="font-size: 13px; color: #7b1fa2; line-height: 1.5;">
                    This report covers <strong>multi-source monitoring</strong>:<br>
                    • <strong>Auto Mode accounts (1,72 → 0,0)</strong>: Legacy high-frequency scanning accounts<br>
                    • <strong>APcampaign accounts (1,12 → 0,0)</strong>: Current campaign-based scanning accounts<br>
                    • <strong>Non-Matching Projects Reset</strong>: Auto mode projects with inactive campaigns/accounts reset to manual<br>
                    • <strong>APNews accounts</strong>: Daily status visibility from APNews.csv
                </div>
            </div>
            """)
            
            # Add summary stats if there are any changes
            if total_all_projects_reset > 0 or total_inactive_found > 0:
                content_parts.append(self.builder.build_summary_stats(stats))
            
            # Add status messages based on results
            if status == "success":
                if total_all_projects_reset > 0:
                    content_parts.append(
                        self.builder.build_success_message(
                            "Comprehensive daily reset completed with configuration updates",
                            f"Auto Mode: Reset {auto_mode_projects_reset} projects from (1,72) to (0,0). "
                            f"APcampaign: Reset {apcampaign_projects_reset} projects from (1,12) to (0,0). "
                            f"Non-Matching: Reset {non_matching_reset} projects with inactive campaigns/accounts. "
                            f"Total: {total_all_projects_reset} projects disabled for inactive accounts."
                        )
                    )
                else:
                    content_parts.append(
                        self.builder.build_success_message(
                            "Comprehensive daily reset completed - all accounts properly configured",
                            f"Monitored {auto_mode_accounts_monitored} Auto Mode accounts and {apcampaign_projects_monitored} APcampaign projects. "
                            f"Checked {non_matching_checked} non-matching projects. "
                            f"All inactive accounts are properly configured - no changes needed."
                        )
                    )
            else:
                error_msg = report_data.get("error_message", "Unknown error occurred")
                content_parts.append(
                    self.builder.build_error_message("Comprehensive daily reset failed", error_msg)
                )
            
            # Add configuration explanation for both types
            content_parts.append("""
            <div style="background-color: #e3f2fd; border: 1px solid #2196f3; padding: 15px; margin: 20px 0; border-radius: 6px;">
                <h4 style="margin: 0 0 10px 0; color: #1565c0;">📋 Configuration Types Explained</h4>
                <div style="font-size: 13px; color: #1976d2; line-height: 1.5;">
                    <strong>Manual Mode (0,0):</strong> Auto-Scan = OFF, Scans Per Day = 0 (No scanning)<br>
                    <strong>Auto Mode (1,72):</strong> Auto-Scan = ON, Scans Per Day = 72 (Legacy high-frequency)<br>
                    <strong>APcampaign Mode (1,12):</strong> Auto-Scan = ON, Scans Per Day = 12 (Current campaign-based)<br><br>
                    <em>Inactive accounts should use Manual Mode (0,0) regardless of their previous configuration.</em>
                </div>
            </div>
            """)
            
            # Process Auto Mode account changes
            recent_auto_accounts = self._filter_recent_changes(accounts_reset)
            
            if recent_auto_accounts:
                priority_accounts = [acc for acc in recent_auto_accounts if "PRIORITY" in acc.get("status", "")]
                inactive_accounts = [acc for acc in recent_auto_accounts if acc.get("auto_scan", 0) == 0 and "PRIORITY" not in acc.get("status", "")]
                
                if priority_accounts:
                    priority_projects = sum(acc.get("total_projects", 0) for acc in priority_accounts)
                    title = f"🚨 PRIORITY AUTO MODE ALERTS (Last 24H) - {len(priority_accounts)} Newly Inactive Accounts ({priority_projects} Projects Reset)"
                    content_parts.append(
                        self.builder.build_account_table(priority_accounts, title, is_priority=True)
                    )
                
                if inactive_accounts:
                    inactive_projects = sum(acc.get("total_projects", 0) for acc in inactive_accounts)
                    title = f"Auto Mode Recent Changes (Last 24H) - {len(inactive_accounts)} Accounts ({inactive_projects} Total Projects)"
                    content_parts.append(
                        self.builder.build_account_table(inactive_accounts, title)
                    )
            
            # Process APcampaign account changes
            if apcampaign_accounts_reset:
                # Create APcampaign table format
                apcampaign_table_html = self._build_apcampaign_table(apcampaign_accounts_reset, apcampaign_reset_success, apcampaign_reset_failures)
                content_parts.append(apcampaign_table_html)

            # Process APNews account status
            if apnews_newly_inactive_accounts:
                apnews_table_html = self._build_apnews_table(apnews_newly_inactive_accounts, apnews_accounts_monitored, apnews_unknown_count)
                content_parts.append(apnews_table_html)
            
            # If no changes at all, show minimal summary
            if not recent_auto_accounts and not apcampaign_accounts_reset and not apnews_newly_inactive_accounts:
                content_parts = [
                    content_parts[0],  # Keep the header
                    """
                <div style="background-color: #e8f5e8; border: 1px solid #4caf50; padding: 20px; margin: 20px 0; border-radius: 6px; text-align: center;">
                    <h3 style="margin: 0 0 15px 0; color: #2e7d32;">✅ No Account Changes Detected</h3>
                    <div style="font-size: 14px; color: #388e3c; line-height: 1.6;">
                        Auto Mode: All {0} accounts remain properly configured.<br>
                        APcampaign: All {1} projects remain properly configured.<br>
                        APNews: {2} accounts monitored ({3} inactive in last 24h, {4} unknown).<br>
                        <strong>Comprehensive monitoring is working correctly.</strong>
                    </div>
                </div>
                """.format(auto_mode_accounts_monitored, apcampaign_projects_monitored, apnews_accounts_monitored, apnews_newly_inactive_count, apnews_unknown_count)
                ]
            
            # Build final email
            main_content = "".join(content_parts)
            
            html_content = self.builder.build_geoedge_email(
                title="GeoEdge Comprehensive Monitoring Report",
                greeting="Hi team,",
                main_content=main_content
            )
            
            # Prepare CSV data for attachment (include both types of changes)
            csv_data = []
            
            # Add Auto Mode account data
            for account in recent_auto_accounts:
                csv_data.append({
                    "Monitoring Type": "Auto Mode (1,72)",
                    "Account ID": account.get("account_id"),
                    "Account Name": account.get("account_name", "N/A"),
                    "Account Status": account.get("status"),
                    "Total Projects": account.get("total_projects", 0),
                    "Auto Scan Setting": account.get("auto_scan", 0),
                    "Scans Per Day": account.get("scans_per_day", 0),
                    "Configuration": f"({account.get('auto_scan', 0)},{account.get('scans_per_day', 0)})",
                    "Projects Reset": account.get("projects_reset", 0),
                    "Last Updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "Scan Status": "Disabled" if (account.get('auto_scan', 0) == 0) else "Enabled"
                })
            
            # Add APcampaign account data  
            for account in apcampaign_accounts_reset:
                csv_data.append({
                    "Monitoring Type": "APcampaign (1,12)",
                    "Account ID": f"Campaign {account.get('campaign_id', 'N/A')}",
                    "Account Name": "N/A",
                    "Account Status": "INACTIVE_CAMPAIGN",
                    "Total Projects": 1,  # Each entry is one project
                    "Auto Scan Setting": 0,  # Now reset to 0
                    "Scans Per Day": 0,  # Now reset to 0
                    "Configuration": account.get('new_config', '0,0'),
                    "Projects Reset": 1 if account.get('reset_success') else 0,
                    "Last Updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "Scan Status": "Disabled" if account.get('reset_success') else "Failed"
                })

            # Add APNews inactive account data
            for account in apnews_newly_inactive_accounts:
                csv_data.append({
                    "Monitoring Type": "APNews Accounts",
                    "Account ID": account.get("account_id"),
                    "Account Name": account.get("account_name", "N/A"),
                    "Account Status": account.get("status", "N/A"),
                    "Total Projects": "N/A",
                    "Auto Scan Setting": "N/A",
                    "Scans Per Day": "N/A",
                    "Configuration": "N/A",
                    "Projects Reset": 0,
                    "Last Updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "Scan Status": "N/A"
                })
            
            # Send email
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            
            # Adjust subject line based on results
            if total_all_projects_reset == 0:
                subject = f"✅ GeoEdge Comprehensive Monitor - No Changes Detected ({date_str})"
            elif status == "success":
                reset_parts = []
                if auto_mode_projects_reset > 0:
                    reset_parts.append(f"Auto:{auto_mode_projects_reset}")
                if apcampaign_projects_reset > 0:
                    reset_parts.append(f"APcampaign:{apcampaign_projects_reset}")
                if non_matching_reset > 0:
                    reset_parts.append(f"NonMatching:{non_matching_reset}")
                
                if reset_parts:
                    subject = f"🔧 GeoEdge Monitor - {' + '.join(reset_parts)} = {total_all_projects_reset} Projects Reset ({date_str})"
                else:
                    subject = f"✅ GeoEdge Comprehensive Monitor - All Accounts Active ({date_str})"
            else:
                subject = f"❌ GeoEdge Comprehensive Monitor - System Error Detected ({date_str})"
            
            csv_filename = f"geoedge_comprehensive_report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}.csv"
            
            return self.sender.send_email(
                subject=subject,
                html_content=html_content,
                csv_data=csv_data if csv_data else None,
                csv_filename=csv_filename if csv_data else None
            )
            
        except Exception as e:
            print(f"❌ Failed to send reset report email: {str(e)}")
            return False
    
    def _build_apcampaign_table(self, apcampaign_accounts: List[Dict], success_count: int, failure_count: int) -> str:
        """Build HTML table for APcampaign account changes"""
        
        title = f"🔧 APcampaign Changes (1,12 → 0,0) - {len(apcampaign_accounts)} Projects ({success_count} Success, {failure_count} Failed)"
        
        # Build table rows
        rows = ""
        for account in apcampaign_accounts:
            status_icon = "✅" if account.get('reset_success') else "❌"
            status_color = "#28a745" if account.get('reset_success') else "#dc3545"
            
            rows += f"""
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 8px; font-size: 11px; font-family: monospace;">{account.get('project_id', 'N/A')[:20]}...</td>
                <td style="padding: 8px; text-align: center;">{account.get('campaign_id', 'N/A')}</td>
                <td style="padding: 8px; font-size: 11px;">{account.get('locations', 'N/A')[:15]}...</td>
                <td style="padding: 8px; text-align: center;">{account.get('old_config', 'N/A')}</td>
                <td style="padding: 8px; text-align: center; color: {status_color}; font-weight: bold;">{status_icon} {account.get('new_config', 'N/A')}</td>
            </tr>
            """
        
        return f"""
        <div style="margin: 20px 0;">
            <h4 style="margin: 0 0 15px 0; color: #1976d2; font-size: 16px;">{title}</h4>
            <table style="width: 100%; border-collapse: collapse; border: 1px solid #ddd; background-color: white;">
                <thead>
                    <tr style="background-color: #f8f9fa;">
                        <th style="padding: 10px 8px; text-align: left; font-size: 12px; font-weight: 600; color: #495057; border-bottom: 2px solid #dee2e6;">Project ID</th>
                        <th style="padding: 10px 8px; text-align: center; font-size: 12px; font-weight: 600; color: #495057; border-bottom: 2px solid #dee2e6;">Campaign</th>
                        <th style="padding: 10px 8px; text-align: left; font-size: 12px; font-weight: 600; color: #495057; border-bottom: 2px solid #dee2e6;">Locations</th>
                        <th style="padding: 10px 8px; text-align: center; font-size: 12px; font-weight: 600; color: #495057; border-bottom: 2px solid #dee2e6;">Old Config</th>
                        <th style="padding: 10px 8px; text-align: center; font-size: 12px; font-weight: 600; color: #495057; border-bottom: 2px solid #dee2e6;">New Config</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </div>
        """
    def _build_apnews_table(self, apnews_accounts: List[Dict], total_monitored: int, unknown_count: int) -> str:
        """Build HTML table for APNews inactive accounts"""

        title = f"📰 APNews Inactive Accounts (Last 24h) - {len(apnews_accounts)} Inactive (Total: {total_monitored}, Unknown: {unknown_count})"

        rows = ""
        for account in apnews_accounts:
            rows += f"""
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 8px; font-size: 11px; font-family: monospace;">{account.get('account_id', 'N/A')}</td>
                <td style="padding: 8px; font-size: 11px;">{account.get('account_name', 'N/A')}</td>
                <td style="padding: 8px; text-align: center;">{account.get('status', 'N/A')}</td>
            </tr>
            """

        return f"""
        <div style="margin: 20px 0;">
            <h4 style="margin: 0 0 15px 0; color: #1976d2; font-size: 16px;">{title}</h4>
            <table style="width: 100%; border-collapse: collapse; border: 1px solid #ddd; background-color: white;">
                <thead>
                    <tr style="background-color: #f8f9fa;">
                        <th style="padding: 10px 8px; text-align: left; font-size: 12px; font-weight: 600; color: #495057; border-bottom: 2px solid #dee2e6;">Account ID</th>
                        <th style="padding: 10px 8px; text-align: left; font-size: 12px; font-weight: 600; color: #495057; border-bottom: 2px solid #dee2e6;">Account Name</th>
                        <th style="padding: 10px 8px; text-align: center; font-size: 12px; font-weight: 600; color: #495057; border-bottom: 2px solid #dee2e6;">Status</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </div>
        """
        
    def _filter_recent_changes(self, accounts_reset: List[Dict]) -> List[Dict]:
        """Filter accounts to only include those with changes in the last 24 hours"""
        from datetime import datetime, timedelta
        
        recent_accounts = []
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        for account in accounts_reset:
            status = account.get("status", "")
            
            # Always include priority newly inactive accounts
            if "PRIORITY" in status or "NEWLY_INACTIVE" in status:
                recent_accounts.append(account)
                continue
            
            # Include accounts that had actual resets (projects_reset > 0)
            projects_reset = account.get("projects_reset", 0)
            if projects_reset > 0:
                recent_accounts.append(account)
                continue
                
            # For other accounts, only include if they have recent timestamps
            # This would need to be implemented based on your specific timestamp fields
            # For now, exclude accounts that seem to be just status quo
            if status in ["RESET_TO_MANUAL", "ACTIVE_AUTO_SCAN"]:
                # Only include if there were actual changes, not just status checks
                continue
        
        return recent_accounts    
    def build_error_message(self, message: str, details: Optional[str] = None) -> str:
        """Build an error message HTML block"""
        details_html = f"<p style=\"margin: 10px 0 0 0; font-size: 13px; color: #d32f2f;\">{details}</p>" if details else ""
        
        return f"""
        <div style="background-color: #ffebee; border-left: 4px solid #f44336; padding: 15px; margin: 20px 0; border-radius: 4px;">
            <p style="margin: 0; font-size: 15px; color: #d32f2f; font-weight: bold;">
                ❌ {message}
            </p>
            {details_html}
        </div>
        """


def send_test_email():
    """Send a test email to verify configuration"""
    reporter = GeoEdgeEmailReporter()
    
    test_data = {
        "total_accounts_checked": 97,
        "inactive_accounts": 4, 
        "active_accounts": 93,
        "total_projects_scanned": 1025,
        "projects_reset": 0,
        "execution_time": 45.2,
        "status": "success",
        "inactive_account_details": [
            {"account_id": "1234567", "status": "INACTIVE", "project_count": 150, "changes_made": 0},
            {"account_id": "2345678", "status": "INACTIVE", "project_count": 200, "changes_made": 0},
        ],
        "active_account_details": [
            {"account_id": "3456789", "status": "ACTIVE", "project_count": 25, "changes_made": 0},
            {"account_id": "4567890", "status": "ACTIVE", "project_count": 10, "changes_made": 0},
        ]
    }
    
    success = reporter.send_daily_reset_report(test_data)
    
    if success:
        print("✅ Test email sent successfully!")
    else:
        print("❌ Failed to send test email")
    
    return success


if __name__ == "__main__":
    print("GeoEdge Email Reporter - Test Mode")
    send_test_email()