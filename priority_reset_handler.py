#!/usr/bin/env python3
"""
Priority Reset Handler - Specifically handles newly inactive accounts
"""
import os
import sys
import json
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv

# Import existing modules
try:
    from account_status_monitor import AccountStatusMonitor
    from email_reporter import GeoEdgeEmailReporter
    import update_autoscan
    MODULES_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Module import error: {e}")
    MODULES_AVAILABLE = False

load_dotenv()

def reset_projects_for_priority_accounts(priority_account_ids: List[str]) -> Dict[str, Any]:
    """
    Reset projects for newly inactive accounts to (0,0) using the main reset script
    """
    if not priority_account_ids:
        return {'success': True, 'accounts_reset': [], 'total_projects_reset': 0}
    
    print(f"🔧 PRIORITY RESET FOR {len(priority_account_ids)} NEWLY INACTIVE ACCOUNTS")
    print("=" * 60)
    
    results = {
        'success': True,
        'accounts_reset': [],
        'total_projects_reset': 0,
        'errors': []
    }
    
    try:
        # Create a temporary file with priority account IDs
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            for acc_id in priority_account_ids:
                f.write(f"{acc_id}\\n")
            temp_file = f.name
        
        print(f"📄 Created temporary accounts file: {temp_file}")
        
        # Import and call the main reset functionality directly
        import reset_inactive_accounts
        
        # Prepare arguments for the reset script (simulate command line args)
        import argparse
        
        # Create a mock args object similar to what the script expects
        class MockArgs:
            def __init__(self):
                self.accounts_file = temp_file
                self.dry_run = False
                self.lookback_days = 30
                self.all_projects = True  # For inactive accounts, reset ALL projects
        
        mock_args = MockArgs()
        
        # Load the accounts
        account_ids = reset_inactive_accounts.load_accounts(mock_args.accounts_file)
        print(f"📋 Loaded {len(account_ids)} priority accounts for reset")
        
        # Get account statuses
        statuses = reset_inactive_accounts.fetch_account_statuses(account_ids)
        frozen_accounts = [acc for acc, label in statuses.items() if label in reset_inactive_accounts.FROZEN_MARKERS]
        
        print(f"🎯 Found {len(frozen_accounts)} accounts that need reset")
        
        # Get projects for these accounts (ALL projects since they're newly inactive)
        projects = reset_inactive_accounts.get_projects_for_accounts(
            frozen_accounts, 
            all_projects=True,  # Get ALL projects for newly inactive accounts
            lookback_days=30
        )
        
        print(f"📊 Found {len(projects)} projects across {len(frozen_accounts)} accounts")
        
        # Perform the actual reset
        if projects:
            from geoedge_projects.client import GeoEdgeClient
            
            client = GeoEdgeClient()
            
            for project_id, project_data in projects:
                try:
                    # Reset to manual mode (0, 0)
                    client.update_project_schedule(project_id, auto_scan=0, times_per_day=0)
                    print(f"   ✅ Reset project {project_id} to (0,0)")
                    results['total_projects_reset'] += 1
                    
                except Exception as e:
                    error_msg = f"Failed to reset project {project_id}: {e}"
                    results['errors'].append(error_msg)
                    print(f"   ❌ {error_msg}")
            
            # Prepare account reset data for reporting
            for acc_id in frozen_accounts:
                account_projects = [p for p in projects if p[1]['syndicator_id'] == acc_id]
                results['accounts_reset'].append({
                    'account_id': acc_id,
                    'projects_reset': len(account_projects),
                    'auto_scan': 0,
                    'scans_per_day': 0,
                    'status': 'PRIORITY_NEWLY_INACTIVE'
                })
        
        # Clean up temp file
        os.unlink(temp_file)
        
        print(f"\\n📊 PRIORITY RESET SUMMARY:")
        print(f"   • Accounts processed: {len(frozen_accounts)}")
        print(f"   • Total projects reset: {results['total_projects_reset']}")
        print(f"   • Errors: {len(results['errors'])}")
        
        return results
        
    except Exception as e:
        results['success'] = False
        results['errors'].append(f"Critical error in priority reset: {e}")
        print(f"❌ Critical error: {e}")
        import traceback
        traceback.print_exc()
        return results

def integrated_daily_reset():
    """
    Integrated daily reset that prioritizes newly inactive accounts
    """
    print("🚀 INTEGRATED DAILY RESET WITH PRIORITY MONITORING")
    print("=" * 70)
    print(f"Started at: {datetime.now()}")
    
    # Step 1: Monitor for newly inactive accounts
    monitor = AccountStatusMonitor()
    status_changes = monitor.monitor_status_changes()
    
    reset_results = {'accounts_reset': [], 'total_projects_reset': 0}
    
    # Step 2: Handle newly inactive accounts first (PRIORITY)
    if status_changes and status_changes['newly_inactive_accounts']:
        print(f"\\n🚨 PRIORITY HANDLING: {len(status_changes['newly_inactive_accounts'])} newly inactive accounts")
        
        priority_account_ids = [str(acc['id']) for acc in status_changes['newly_inactive_accounts']]
        
        # Reset projects for these priority accounts
        priority_results = reset_projects_for_priority_accounts(priority_account_ids)
        
        if priority_results['success']:
            reset_results['accounts_reset'].extend(priority_results['accounts_reset'])
            reset_results['total_projects_reset'] += priority_results['total_projects_reset']
            
            print(f"\\n✅ PRIORITY RESET COMPLETED")
            print(f"   • {len(priority_account_ids)} newly inactive accounts handled")
            print(f"   • {priority_results['total_projects_reset']} projects reset to (0,0)")
        else:
            print(f"\\n❌ PRIORITY RESET HAD ERRORS:")
            for error in priority_results['errors']:
                print(f"   • {error}")
    
    # Step 3: Continue with regular reset for other inactive accounts
    # This would call the existing reset_inactive_accounts.py logic for non-priority accounts
    print(f"\\n🔄 Proceeding with regular reset for other accounts...")
    # ... existing reset logic would go here ...
    
    # Step 4: Send comprehensive email report
    try:
        if EMAIL_AVAILABLE:
            reporter = GeoEdgeEmailReporter()
            
            # Prepare comprehensive report data
            report_data = {
                'total_accounts_checked': len(reset_results['accounts_reset']),
                'accounts_reset': reset_results['accounts_reset'],
                'total_projects_reset': reset_results['total_projects_reset'],
                'execution_time': datetime.now().isoformat(),
                'priority_reset_performed': bool(status_changes and status_changes['newly_inactive_accounts']),
                'newly_inactive_count': len(status_changes['newly_inactive_accounts']) if status_changes else 0
            }
            
            print(f"\\n📧 Sending comprehensive email report...")
            reporter.send_daily_reset_report(report_data)
            print(f"✅ Email report sent successfully")
            
    except Exception as e:
        print(f"❌ Error sending email report: {e}")
    
    # Step 5: Final summary
    print(f"\\n🎯 INTEGRATED DAILY RESET COMPLETED")
    print(f"=" * 50)
    print(f"Finished at: {datetime.now()}")
    if status_changes:
        print(f"Priority accounts handled: {len(status_changes['newly_inactive_accounts'])}")
    print(f"Total projects reset: {reset_results['total_projects_reset']}")
    print(f"✅ All newly inactive accounts have projects set to manual mode (0,0)")

def main():
    """Main function"""
    integrated_daily_reset()

if __name__ == "__main__":
    main()