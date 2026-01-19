#!/usr/bin/env python3
"""
Enhanced Account Status Monitor - Detects newly inactive accounts requiring immediate reset
"""
import os
import sys
import json
import pymysql
from datetime import datetime, timedelta
from dotenv import load_dotenv
from typing import List, Dict, Set, Tuple

load_dotenv()

def _env_or_fail(key: str) -> str:
    value = os.getenv(key)
    if value is None:
        raise ValueError(f"Environment variable {key} is not set")
    return value

class AccountStatusMonitor:
    def __init__(self):
        self.host = _env_or_fail("MYSQL_HOST")
        self.port = int(os.getenv("MYSQL_PORT", "3306"))
        self.user = _env_or_fail("MYSQL_USER")
        self.password = _env_or_fail("MYSQL_PASSWORD")
        self.database = _env_or_fail("MYSQL_DB")
        
        self.baseline_file = "/tmp/account_status_baseline.json"
        
    def connect_db(self):
        return pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    
    def get_current_account_statuses(self) -> Dict[int, Dict]:
        """Get current status of all accounts"""
        db = self.connect_db()
        cursor = db.cursor()
        
        cursor.execute("""
            SELECT 
                id,
                name,
                status,
                update_time,
                inactivity_date,
                status_change_reason
            FROM publishers 
            WHERE status IN ('LIVE', 'ACTIVE', 'INACTIVE')
            ORDER BY id
        """)
        
        accounts = {}
        for row in cursor.fetchall():
            accounts[row['id']] = {
                'name': row['name'],
                'status': row['status'],
                'update_time': row['update_time'].isoformat() if row['update_time'] else None,
                'inactivity_date': row['inactivity_date'].isoformat() if row['inactivity_date'] else None,
                'status_change_reason': row['status_change_reason']
            }
        
        cursor.close()
        db.close()
        
        return accounts
    
    def save_baseline(self, accounts: Dict[int, Dict]) -> None:
        """Save current account statuses as baseline"""
        baseline_data = {
            'timestamp': datetime.now().isoformat(),
            'accounts': accounts
        }
        
        with open(self.baseline_file, 'w') as f:
            json.dump(baseline_data, f, indent=2)
        
        print(f"✅ Baseline saved: {len(accounts)} accounts")
    
    def load_baseline(self) -> Tuple[Dict[int, Dict], datetime]:
        """Load previous baseline"""
        try:
            with open(self.baseline_file, 'r') as f:
                data = json.load(f)
            
            # Convert string keys back to integers
            accounts = {int(k): v for k, v in data['accounts'].items()}
            timestamp = datetime.fromisoformat(data['timestamp'])
            
            return accounts, timestamp
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return {}, datetime.min
    
    def find_newly_inactive_accounts(self) -> List[Dict]:
        """Find accounts that became inactive since last baseline (within 24 hours only)"""
        current_accounts = self.get_current_account_statuses()
        baseline_accounts, baseline_time = self.load_baseline()
        
        newly_inactive = []
        
        if not baseline_accounts:
            print("⚠️ No baseline found. Creating initial baseline...")
            self.save_baseline(current_accounts)
            return []
        
        # Only consider changes if baseline is less than 24 hours old
        hours_since_baseline = (datetime.now() - baseline_time).total_seconds() / 3600
        if hours_since_baseline > 24:
            print(f"⚠️ Baseline is {hours_since_baseline:.1f} hours old. Only showing very recent changes...")
        
        print(f"🔍 Comparing with baseline from {baseline_time}")
        
        for account_id, current_data in current_accounts.items():
            current_status = current_data['status']
            
            # Check if this account exists in baseline
            if account_id in baseline_accounts:
                baseline_status = baseline_accounts[account_id]['status']
                
                # Found a newly inactive account!
                if baseline_status in ['LIVE', 'ACTIVE'] and current_status == 'INACTIVE':
                    # Double-check with database timestamps to ensure it's within 24 hours
                    if self._is_change_within_24_hours(current_data):
                        newly_inactive.append({
                            'id': account_id,
                            'name': current_data['name'],
                            'old_status': baseline_status,
                            'new_status': current_status,
                            'change_reason': current_data['status_change_reason'],
                            'inactivity_date': current_data['inactivity_date']
                        })
        
        return newly_inactive
    
    def _is_change_within_24_hours(self, account_data: Dict) -> bool:
        """Verify that the account change occurred within the last 24 hours"""
        try:
            # Check inactivity_date first
            if account_data.get('inactivity_date'):
                inactivity_date = datetime.fromisoformat(account_data['inactivity_date'])
                hours_ago = (datetime.now() - inactivity_date).total_seconds() / 3600
                if hours_ago <= 24:
                    return True
            
            # Check update_time as fallback
            if account_data.get('update_time'):
                update_time = datetime.fromisoformat(account_data['update_time'])
                hours_ago = (datetime.now() - update_time).total_seconds() / 3600
                if hours_ago <= 24:
                    return True
                    
            return False
        except Exception:
            # If we can't parse dates, assume it's recent to be safe
            return True
    
    def get_projects_for_accounts(self, account_ids: List[int]) -> Dict[int, Dict]:
        """Get project counts for specific accounts"""
        if not account_ids:
            return {}
        
        db = self.connect_db()
        cursor = db.cursor()
        
        placeholders = ','.join(['%s'] * len(account_ids))
        cursor.execute(f"""
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
            WHERE p.id IN ({placeholders})
            GROUP BY p.id, p.name, p.status
        """, account_ids)
        
        projects_data = {}
        for row in cursor.fetchall():
            projects_data[row['publisher_id']] = {
                'name': row['publisher_name'],
                'status': row['publisher_status'],
                'total_projects': row['total_projects'] or 0,
                'total_campaigns': row['total_campaigns'] or 0,
                'active_campaigns': row['active_campaigns'] or 0,
                'latest_project_date': row['latest_project_date'].isoformat() if row['latest_project_date'] else None
            }
        
        cursor.close()
        db.close()
        
        return projects_data
    
    def monitor_status_changes(self) -> Dict:
        """Main monitoring function - returns newly inactive accounts with their projects"""
        print("🔍 MONITORING ACCOUNT STATUS CHANGES")
        print("=" * 50)
        
        newly_inactive = self.find_newly_inactive_accounts()
        
        if not newly_inactive:
            print("✅ No newly inactive accounts found")
            return {'newly_inactive_accounts': [], 'total_projects_need_reset': 0}
        
        print(f"🚨 Found {len(newly_inactive)} newly inactive accounts:")
        
        account_ids = [acc['id'] for acc in newly_inactive]
        projects_data = self.get_projects_for_accounts(account_ids)
        
        total_projects_need_reset = 0
        results = []
        
        print("\\n   Account ID  Name                    Old→New     Projects  Campaigns")
        print("   " + "-" * 75)
        
        for acc in newly_inactive:
            acc_id = acc['id']
            project_info = projects_data.get(acc_id, {})
            project_count = project_info.get('total_projects', 0)
            campaign_count = project_info.get('total_campaigns', 0)
            
            total_projects_need_reset += project_count
            
            result = {
                **acc,
                'project_info': project_info
            }
            results.append(result)
            
            print(f"   {acc_id: <10} {acc['name'][:23]: <23} {acc['old_status']}→{acc['new_status']: <7} "
                  f"{project_count: >8} {campaign_count: >9}")
        
        print(f"\\n🎯 TOTAL PROJECTS NEEDING IMMEDIATE RESET: {total_projects_need_reset}")
        
        # Update baseline with current state
        current_accounts = self.get_current_account_statuses()
        self.save_baseline(current_accounts)
        
        return {
            'newly_inactive_accounts': results,
            'total_projects_need_reset': total_projects_need_reset,
            'timestamp': datetime.now().isoformat()
        }

def main():
    try:
        monitor = AccountStatusMonitor()
        
        # Check for newly inactive accounts
        results = monitor.monitor_status_changes()
        
        # If there are newly inactive accounts, output the information needed
        # for the reset script to prioritize them
        if results['newly_inactive_accounts']:
            priority_accounts = [str(acc['id']) for acc in results['newly_inactive_accounts']]
            print(f"\\n📋 PRIORITY ACCOUNT IDs FOR IMMEDIATE RESET:")
            print(f"   {','.join(priority_accounts)}")
            
            # Save to file for integration with main reset script
            priority_file = "/tmp/priority_reset_accounts.json"
            with open(priority_file, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"   📄 Priority list saved to: {priority_file}")
        
        return results
        
    except Exception as e:
        print(f"❌ Error during monitoring: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    main()