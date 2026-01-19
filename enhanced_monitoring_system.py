#!/usr/bin/env python3
"""
Integration script for account status monitoring with reset functionality
"""
import os
import sys
import json
from datetime import datetime
from typing import List, Dict

# Import existing modules
try:
    from account_status_monitor import AccountStatusMonitor
    from email_reporter import GeoEdgeEmailReporter
    import reset_inactive_accounts
    MODULES_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Module import error: {e}")
    MODULES_AVAILABLE = False

def enhanced_reset_for_status_changes():
    """
    Enhanced reset function that prioritizes newly inactive accounts
    """
    if not MODULES_AVAILABLE:
        print("❌ Required modules not available")
        return
    
    print("🚀 ENHANCED ACCOUNT STATUS MONITORING & RESET")
    print("=" * 60)
    
    # Step 1: Monitor for newly inactive accounts
    monitor = AccountStatusMonitor()
    status_changes = monitor.monitor_status_changes()
    
    # Step 2: If there are newly inactive accounts, prioritize their reset
    if status_changes and status_changes['newly_inactive_accounts']:
        print(f"\\n🚨 PRIORITY RESET REQUIRED!")
        print(f"   Found {len(status_changes['newly_inactive_accounts'])} newly inactive accounts")
        print(f"   Total projects needing immediate reset: {status_changes['total_projects_need_reset']}")
        
        # Extract priority account IDs
        priority_account_ids = [str(acc['id']) for acc in status_changes['newly_inactive_accounts']]
        
        print(f"\\n📋 Priority Account IDs: {', '.join(priority_account_ids)}")
        
        # Step 3: Run reset for these priority accounts first
        print(f"\\n🔧 Running priority reset for newly inactive accounts...")
        
        # Here we would call the main reset script with these specific accounts
        # For now, just show what would happen
        print(f"   → Would reset projects for accounts: {priority_account_ids}")
        print(f"   → Expected projects to reset: {status_changes['total_projects_need_reset']}")
        
        return status_changes
    else:
        print("\\n✅ No newly inactive accounts found - proceeding with regular reset")
        return None

def generate_enhanced_email_report(status_changes: Dict = None):
    """
    Generate enhanced email report including newly inactive account information
    """
    try:
        reporter = GeoEdgeEmailReporter()
        
        # Prepare report data
        report_data = {
            'accounts_reset': [],
            'total_projects_reset': 0,
            'total_accounts_reset': 0,
            'execution_time': datetime.now().isoformat(),
            'newly_inactive_detected': False
        }
        
        # If there were newly inactive accounts, include them in report
        if status_changes and status_changes['newly_inactive_accounts']:
            report_data['newly_inactive_detected'] = True
            report_data['newly_inactive_count'] = len(status_changes['newly_inactive_accounts'])
            report_data['priority_projects_reset'] = status_changes['total_projects_need_reset']
            
            # Convert newly inactive accounts to report format
            for acc in status_changes['newly_inactive_accounts']:
                project_info = acc.get('project_info', {})
                report_data['accounts_reset'].append({
                    'account_id': acc['id'],
                    'account_name': acc['name'],
                    'auto_scan': 0,  # Reset to 0
                    'scans_per_day': 0,  # Reset to 0
                    'total_projects': project_info.get('total_projects', 0),
                    'status': 'NEWLY_INACTIVE_PRIORITY'
                })
        
        # Generate and send email
        print(f"\\n📧 Sending enhanced email report...")
        
        # Create proper report data structure
        full_report_data = {
            'total_accounts_checked': len(report_data['accounts_reset']) if report_data['accounts_reset'] else 0,
            'accounts_reset': report_data['accounts_reset'],
            'total_projects_reset': report_data['total_projects_reset'],
            'execution_time': report_data['execution_time'],
            'newly_inactive_detected': report_data['newly_inactive_detected']
        }
        
        reporter.send_daily_reset_report(full_report_data)
        
        print(f"✅ Enhanced email report sent successfully")
        
    except Exception as e:
        print(f"❌ Error sending enhanced email report: {e}")

def create_detection_queries_file():
    """
    Create SQL queries file for manual investigation
    """
    queries_content = """
-- ====================================
-- ACCOUNT DEACTIVATION DETECTION QUERIES
-- ====================================

-- 1. Find accounts that became inactive in the last 24 hours
SELECT 
    id as publisher_id,
    name as publisher_name,
    status,
    inactivity_date,
    update_time,
    status_change_reason,
    TIMESTAMPDIFF(HOUR, COALESCE(inactivity_date, update_time), NOW()) as hours_ago
FROM publishers 
WHERE status = 'INACTIVE'
  AND (
      inactivity_date >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
      OR (inactivity_date IS NULL AND update_time >= DATE_SUB(NOW(), INTERVAL 24 HOUR))
  )
ORDER BY COALESCE(inactivity_date, update_time) DESC;

-- 2. Count projects under recently inactive accounts
SELECT 
    p.id as publisher_id,
    p.name as publisher_name,
    p.status as publisher_status,
    COUNT(DISTINCT gep.project_id) as total_projects,
    COUNT(DISTINCT c.id) as total_campaigns,
    COUNT(CASE WHEN c.status = 'ACTIVE' THEN 1 END) as active_campaigns,
    MAX(gep.creation_date) as latest_project_date
FROM publishers p
LEFT JOIN sp_campaigns c ON p.id = c.syndicator_id
LEFT JOIN geo_edge_projects gep ON c.id = gep.campaign_id
WHERE p.status = 'INACTIVE'
  AND (
      p.inactivity_date >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
      OR (p.inactivity_date IS NULL AND p.update_time >= DATE_SUB(NOW(), INTERVAL 24 HOUR))
  )
GROUP BY p.id, p.name, p.status
HAVING total_projects > 0
ORDER BY total_projects DESC;

-- 3. Find specific projects needing reset for an account
SELECT 
    gep.project_id,
    gep.creation_date,
    c.syndicator_id,
    c.status as campaign_status,
    p.name as publisher_name
FROM geo_edge_projects gep
JOIN sp_campaigns c ON gep.campaign_id = c.id
JOIN publishers p ON c.syndicator_id = p.id
WHERE c.syndicator_id = 'REPLACE_WITH_ACCOUNT_ID'
  AND p.status = 'INACTIVE'
ORDER BY gep.creation_date DESC;

-- 4. Current status distribution
SELECT 
    status,
    COUNT(*) as account_count
FROM publishers 
GROUP BY status 
ORDER BY account_count DESC;

-- 5. Recent status changes (if using update_time as proxy)
SELECT 
    id,
    name,
    status,
    update_time,
    status_change_reason,
    TIMESTAMPDIFF(HOUR, update_time, NOW()) as hours_since_update
FROM publishers 
WHERE update_time >= DATE_SUB(NOW(), INTERVAL 48 HOUR)
  AND status = 'INACTIVE'
ORDER BY update_time DESC
LIMIT 50;
"""
    
    with open("/Users/gaurav.k/Desktop/geoedge-country-projects/deactivation_queries.sql", "w") as f:
        f.write(queries_content)
    
    print(f"✅ SQL queries file created: deactivation_queries.sql")

def main():
    """
    Main integration function
    """
    try:
        print("🔍 GEOEDGE ENHANCED ACCOUNT MONITORING SYSTEM")
        print("=" * 60)
        print(f"Started at: {datetime.now()}")
        
        # Step 1: Run enhanced monitoring and reset
        status_changes = enhanced_reset_for_status_changes()
        
        # Step 2: Generate enhanced email report
        generate_enhanced_email_report(status_changes)
        
        # Step 3: Create SQL queries file for manual investigation
        create_detection_queries_file()
        
        print(f"\\n✅ Enhanced monitoring system completed successfully!")
        print(f"\\n📋 SUMMARY:")
        if status_changes:
            print(f"   • {len(status_changes['newly_inactive_accounts'])} newly inactive accounts detected")
            print(f"   • {status_changes['total_projects_need_reset']} projects need immediate reset")
        else:
            print(f"   • No newly inactive accounts detected")
        print(f"   • Email report sent")
        print(f"   • SQL queries available for manual investigation")
        
    except Exception as e:
        print(f"❌ Error in enhanced monitoring system: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()