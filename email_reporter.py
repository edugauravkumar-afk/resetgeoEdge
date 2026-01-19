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
    def build_account_table(accounts: List[Dict[str, Any]], title: str = "Account Details") -> str:
        """Build a styled table for account information with scan configuration details"""
        if not accounts:
            return f"<p><em>No {title.lower()} to display.</em></p>"
        
        header_cells = """
        <th style="padding: 12px; border: 1px solid #ddd; background-color: #1a73e8; color: white; font-size: 13px;">Account ID</th>
        <th style="padding: 12px; border: 1px solid #ddd; background-color: #1a73e8; color: white; font-size: 13px;">Status</th>
        <th style="padding: 12px; border: 1px solid #ddd; background-color: #1a73e8; color: white; font-size: 13px;">Total Projects</th>
        <th style="padding: 12px; border: 1px solid #ddd; background-color: #1a73e8; color: white; font-size: 13px;">Auto Scan</th>
        <th style="padding: 12px; border: 1px solid #ddd; background-color: #1a73e8; color: white; font-size: 13px;">Scans Per Day</th>
        <th style="padding: 12px; border: 1px solid #ddd; background-color: #1a73e8; color: white; font-size: 13px;">Configuration</th>
        <th style="padding: 12px; border: 1px solid #ddd; background-color: #1a73e8; color: white; font-size: 13px;">Changes Made</th>
        """
        
        rows = ""
        for account in accounts:
            status_color = "#4caf50" if account.get("status") == "ACTIVE" else "#ff9800"
            changes_made = account.get("changes_made", 0)
            changes_color = "#ff5722" if changes_made > 0 else "#4caf50"
            
            # Get scan configuration
            auto_scan = account.get("auto_scan", 0)
            scans_per_day = account.get("scans_per_day", 0)
            
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
            <tr>
                <td style="padding: 10px; border: 1px solid #ddd; font-family: monospace;">{account.get('account_id', 'N/A')}</td>
                <td style="padding: 10px; border: 1px solid #ddd;">
                    <span style="background: {status_color}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">
                        {account.get('status', 'UNKNOWN')}
                    </span>
                </td>
                <td style="padding: 10px; border: 1px solid #ddd; text-align: center; font-weight: bold;">{account.get('project_count', 0)}</td>
                <td style="padding: 10px; border: 1px solid #ddd; text-align: center; font-family: monospace;">{auto_scan}</td>
                <td style="padding: 10px; border: 1px solid #ddd; text-align: center; font-family: monospace;">{scans_per_day}</td>
                <td style="padding: 10px; border: 1px solid #ddd; text-align: center;">
                    <span style="color: {config_color}; font-weight: bold;">{config_icon} {config_status}</span>
                </td>
                <td style="padding: 10px; border: 1px solid #ddd; text-align: center; color: {changes_color}; font-weight: bold;">{changes_made}</td>
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
        Send daily reset report email.
        
        Args:
            report_data: Dictionary containing:
                - total_accounts_checked: int
                - inactive_accounts: int  
                - active_accounts: int
                - total_projects_scanned: int
                - projects_reset: int
                - inactive_account_details: List[Dict]
                - active_account_details: List[Dict] 
                - execution_time: float
                - status: "success" | "error"
                - error_message: str (if status is error)
        """
        
        try:
            # Determine overall status
            status = report_data.get("status", "success")
            projects_reset = report_data.get("projects_reset", 0)
            
            # Build summary statistics
            stats = {
                "Total Accounts": report_data.get("total_accounts_checked", 0),
                "Inactive Accounts": report_data.get("inactive_accounts", 0),
                "Active Accounts": report_data.get("active_accounts", 0),
                "Projects Scanned": report_data.get("total_projects_scanned", 0),
                "Projects Reset": projects_reset,
                "Execution Time": f"{report_data.get('execution_time', 0):.1f}s"
            }
            
            # Build main content
            content_parts = []
            
            # Add summary stats
            content_parts.append(self.builder.build_summary_stats(stats))
            
            # Add status message
            if status == "success":
                if projects_reset > 0:
                    content_parts.append(
                        self.builder.build_success_message(
                            "Daily reset completed with configuration updates",
                            f"Reset {projects_reset} projects from Auto-Scan (1,72) to Manual Mode (0,0). "
                            f"This disables automatic scanning for inactive accounts to save resources."
                        )
                    )
                else:
                    total_inactive_projects = sum(acc.get("project_count", 0) for acc in report_data.get("inactive_account_details", []))
                    inactive_count = report_data.get("inactive_accounts", 0)
                    content_parts.append(
                        self.builder.build_success_message(
                            "Daily reset completed - all projects properly configured",
                            f"All {total_inactive_projects} projects under {inactive_count} inactive accounts "
                            f"are already set to Manual Mode (0,0) - no scanning will occur."
                        )
                    )
            else:
                error_msg = report_data.get("error_message", "Unknown error occurred")
                content_parts.append(
                    self.builder.build_error_message("Daily reset failed", error_msg)
                )
            
            # Add configuration explanation
            content_parts.append("""
            <div style="background-color: #e3f2fd; border: 1px solid #2196f3; padding: 15px; margin: 20px 0; border-radius: 6px;">
                <h4 style="margin: 0 0 10px 0; color: #1565c0;">📋 Configuration Explained</h4>
                <div style="font-size: 13px; color: #1976d2; line-height: 1.5;">
                    <strong>Manual Mode (0,0):</strong> Auto-Scan = 0 (OFF), Scans Per Day = 0 (No scanning)<br>
                    <strong>Auto Mode (1,72):</strong> Auto-Scan = 1 (ON), Scans Per Day = 72 (Full scanning)<br><br>
                    <em>Inactive accounts should use Manual Mode (0,0) to prevent unnecessary resource usage and costs.</em>
                </div>
            </div>
            """)
            
            # Add account details
            inactive_accounts = report_data.get("inactive_account_details", [])
            if inactive_accounts:
                total_inactive = report_data.get("inactive_accounts", len(inactive_accounts))
                total_inactive_projects = sum(acc.get("project_count", 0) for acc in inactive_accounts)
                title = f"Inactive Accounts - All {len(inactive_accounts)} Accounts ({total_inactive_projects} Total Projects)"
                content_parts.append(
                    self.builder.build_account_table(inactive_accounts, title)
                )
            
            active_accounts = report_data.get("active_account_details", [])
            if active_accounts:
                total_active = report_data.get("active_accounts", 0)
                total_active_projects = sum(acc.get("project_count", 0) for acc in active_accounts)
                
                if len(active_accounts) < total_active:
                    title = f"Recent Active Accounts - Sample {len(active_accounts)} of {total_active} Total ({total_active_projects} Projects Shown)"
                else:
                    title = f"Active Accounts - All {len(active_accounts)} Accounts ({total_active_projects} Total Projects)"
                    
                content_parts.append(
                    self.builder.build_account_table(active_accounts, title)
                )
            
            # Build final email
            main_content = "".join(content_parts)
            
            html_content = self.builder.build_geoedge_email(
                title="GeoEdge Daily Reset Report",
                greeting="Hi team,",
                main_content=main_content
            )
            
            # Prepare CSV data for attachment
            csv_data = []
            all_accounts = (report_data.get("inactive_account_details", []) + 
                           report_data.get("active_account_details", []))
            
            for account in all_accounts:
                csv_data.append({
                    "Account ID": account.get("account_id"),
                    "Account Status": account.get("status"),
                    "Total Projects": account.get("project_count", 0),
                    "Auto Scan Setting": account.get("auto_scan", 0),
                    "Scans Per Day": account.get("scans_per_day", 0),
                    "Configuration": f"({account.get('auto_scan', 0)},{account.get('scans_per_day', 0)})",
                    "Configuration Type": "Manual Mode" if (account.get('auto_scan', 0) == 0 and account.get('scans_per_day', 0) == 0) else "Auto Mode" if (account.get('auto_scan', 0) == 1 and account.get('scans_per_day', 0) == 72) else "Custom",
                    "Changes Made": account.get("changes_made", 0),
                    "Last Updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "Scan Status": "Disabled" if (account.get('auto_scan', 0) == 0 and account.get('scans_per_day', 0) == 0) else "Enabled"
                })
            
            # Send email
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            
            if status == "success":
                if projects_reset > 0:
                    subject = f"🔧 GeoEdge Daily Reset - {projects_reset} Projects Updated ({date_str})"
                else:
                    subject = f"✅ GeoEdge Daily Reset - All Projects Configured ({date_str})"
            else:
                subject = f"❌ GeoEdge Daily Reset - Error ({date_str})"
            
            csv_filename = f"geoedge_reset_report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}.csv"
            
            return self.sender.send_email(
                subject=subject,
                html_content=html_content,
                csv_data=csv_data if csv_data else None,
                csv_filename=csv_filename if csv_data else None
            )
            
        except Exception as e:
            print(f"❌ Failed to send reset report email: {str(e)}")
            return False
    
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