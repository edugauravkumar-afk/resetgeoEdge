#!/usr/bin/env python3
"""
Target Accounts Analysis - Deep Research
Analyzes the specific accounts that were configured for Auto Mode and tracks their current status
"""

import logging
import pymysql
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv
import os

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# These are the target accounts that were configured with Auto Mode from reset_inactive_accounts.py
TARGET_ACCOUNTS = [
    "1290644", "1466060", "1835770", "1623554", "1756429", "1855313", "1724820",
    "1639660", "1786547", "1527715", "1243928", "1343639", "1341693", "1880307",
    "1756440", "1782473", "1487226", "1457895", "1905088", "1154814", "1847769",
    "1878595", "1887104", "1341694", "1343644", "1401160", "1474131", "1204587",
    "1829970", "1828308", "1642145", "1702248", "1829976", "1040822", "1341695",
    "1784283", "1562293", "1892692", "1008114", "1827440", "1896474", "1896475",
    "1896473", "1787788", "1878691", "1688532", "1702259", "1593978", "1077096",
    "1162266", "1510736", "1691715", "1524612", "1661493", "1878358", "1421191",
    "1071765", "1705266", "1154809", "1688849", "1775713", "1798665", "1813041",
    "1756427", "1693504", "1813037", "1601637", "1902380", "1878765", "1243922",
    "1881185", "1147892", "1891323", "1878359", "1661494", "1718765", "1823276",
    "1895053", "1896927", "1784361", "1896472", "1702256", "1039024", "1341696",
    "1900040", "1874354", "1171184", "1766414", "1878372", "1908584", "1894751",
    "1162263", "1346833", "1243926", "1907682", "1535686", "1867619"
]

class TargetAccountsAnalyzer:
    """Analyze the specific target accounts that were configured"""
    
    def __init__(self):
        self.db_config = {
            'host': os.getenv('MYSQL_HOST', 'proxysql-office.taboolasyndication.com'),
            'port': int(os.getenv('MYSQL_PORT', 6033)),
            'user': os.getenv('MYSQL_USER', 'gaurav.k'),
            'password': os.getenv('MYSQL_PASSWORD'),
            'database': os.getenv('MYSQL_DB', 'trc'),
            'charset': 'utf8mb4'
        }
    
    def _get_db_connection(self):
        """Create database connection"""
        return pymysql.connect(**self.db_config)
    
    def analyze_target_accounts_status(self) -> Dict[str, Any]:
        """Analyze current status of all target accounts"""
        db = self._get_db_connection()
        cursor = db.cursor(pymysql.cursors.DictCursor)
        
        account_analysis = {
            'total_target_accounts': len(TARGET_ACCOUNTS),
            'found_in_database': 0,
            'active_accounts': 0,
            'inactive_accounts': 0,
            'not_found': 0,
            'detailed_status': [],
            'status_breakdown': {},
            'accounts_with_projects': 0,
            'total_projects_in_target_accounts': 0
        }
        
        try:
            # Convert account IDs to integers for query
            account_ids = [int(acc_id) for acc_id in TARGET_ACCOUNTS]
            
            # Get detailed info for all target accounts
            placeholders = ','.join(['%s'] * len(account_ids))
            query = f"""
                SELECT 
                    p.id as account_id,
                    p.name as account_name,
                    p.status,
                    p.status_change_reason,
                    p.status_change_performer,
                    p.update_time,
                    p.inactivity_date,
                    COUNT(DISTINCT gep.project_id) as project_count,
                    MAX(gep.creation_date) as latest_project_date,
                    DATEDIFF(NOW(), MAX(gep.creation_date)) as days_since_last_project
                FROM publishers p
                LEFT JOIN sp_campaigns sc ON p.id = sc.syndicator_id
                LEFT JOIN geo_edge_projects gep ON sc.id = gep.campaign_id
                WHERE p.id IN ({placeholders})
                GROUP BY p.id, p.name, p.status, p.status_change_reason, p.status_change_performer, p.update_time, p.inactivity_date
                ORDER BY p.id
            """
            
            cursor.execute(query, account_ids)
            results = cursor.fetchall()
            
            found_ids = set()
            
            for row in results:
                found_ids.add(str(row['account_id']))
                
                account_info = {
                    'account_id': str(row['account_id']),
                    'account_name': row['account_name'],
                    'status': row['status'],
                    'status_change_reason': row['status_change_reason'],
                    'status_change_performer': row['status_change_performer'],
                    'update_time': row['update_time'].isoformat() if row['update_time'] else None,
                    'inactivity_date': row['inactivity_date'].isoformat() if row['inactivity_date'] else None,
                    'project_count': row['project_count'] or 0,
                    'latest_project_date': row['latest_project_date'].isoformat() if row['latest_project_date'] else None,
                    'days_since_last_project': row['days_since_last_project']
                }
                
                # Categorize account status
                if row['status'] == 'active':
                    account_analysis['active_accounts'] += 1
                else:
                    account_analysis['inactive_accounts'] += 1
                
                # Count status types
                status = row['status']
                if status in account_analysis['status_breakdown']:
                    account_analysis['status_breakdown'][status] += 1
                else:
                    account_analysis['status_breakdown'][status] = 1
                
                # Count projects
                if row['project_count'] and row['project_count'] > 0:
                    account_analysis['accounts_with_projects'] += 1
                    account_analysis['total_projects_in_target_accounts'] += row['project_count']
                
                account_analysis['detailed_status'].append(account_info)
            
            account_analysis['found_in_database'] = len(results)
            
            # Find accounts not found in database
            not_found = set(TARGET_ACCOUNTS) - found_ids
            account_analysis['not_found'] = len(not_found)
            account_analysis['not_found_accounts'] = list(not_found)
            
        except Exception as e:
            logger.error(f"Error analyzing target accounts: {e}")
            
        finally:
            cursor.close()
            db.close()
        
        return account_analysis
    
    def get_recent_changes_in_targets(self) -> List[Dict]:
        """Get recent status changes specifically for target accounts"""
        db = self._get_db_connection()
        cursor = db.cursor(pymysql.cursors.DictCursor)
        
        try:
            account_ids = [int(acc_id) for acc_id in TARGET_ACCOUNTS]
            placeholders = ','.join(['%s'] * len(account_ids))
            
            cursor.execute(f"""
                SELECT 
                    p.id as account_id,
                    p.name as account_name,
                    p.status,
                    p.status_change_reason,
                    p.update_time,
                    p.inactivity_date,
                    COUNT(DISTINCT gep.project_id) as project_count
                FROM publishers p
                LEFT JOIN sp_campaigns sc ON p.id = sc.syndicator_id
                LEFT JOIN geo_edge_projects gep ON sc.id = gep.campaign_id
                WHERE p.id IN ({placeholders})
                AND p.update_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                GROUP BY p.id, p.name, p.status, p.status_change_reason, p.update_time, p.inactivity_date
                ORDER BY p.update_time DESC
            """, account_ids)
            
            results = cursor.fetchall()
            
            recent_changes = []
            for row in results:
                recent_changes.append({
                    'account_id': str(row['account_id']),
                    'account_name': row['account_name'],
                    'status': row['status'],
                    'status_change_reason': row['status_change_reason'],
                    'update_time': row['update_time'].isoformat() if row['update_time'] else None,
                    'inactivity_date': row['inactivity_date'].isoformat() if row['inactivity_date'] else None,
                    'project_count': row['project_count'] or 0
                })
            
            return recent_changes
            
        except Exception as e:
            logger.error(f"Error getting recent changes: {e}")
            return []
        finally:
            cursor.close()
            db.close()
    
    def generate_target_accounts_report(self) -> Dict[str, Any]:
        """Generate comprehensive report for target accounts"""
        logger.info("🎯 Analyzing target accounts that were configured for Auto Mode...")
        
        # Analyze current status
        status_analysis = self.analyze_target_accounts_status()
        
        # Get recent changes
        recent_changes = self.get_recent_changes_in_targets()
        
        # Generate summary
        report = {
            'analysis_timestamp': datetime.now().isoformat(),
            'target_accounts_summary': status_analysis,
            'recent_changes_in_targets': recent_changes,
            'key_insights': self._generate_insights(status_analysis, recent_changes)
        }
        
        return report
    
    def _generate_insights(self, status_analysis: Dict, recent_changes: List[Dict]) -> List[str]:
        """Generate key insights about target accounts"""
        insights = []
        
        total = status_analysis['total_target_accounts']
        found = status_analysis['found_in_database']
        active = status_analysis['active_accounts']
        inactive = status_analysis['inactive_accounts']
        not_found = status_analysis['not_found']
        with_projects = status_analysis['accounts_with_projects']
        total_projects = status_analysis['total_projects_in_target_accounts']
        
        insights.append(f"🎯 Target accounts analyzed: {total} accounts")
        insights.append(f"📊 Found in database: {found}/{total} ({found/total*100:.1f}%)")
        
        if not_found > 0:
            insights.append(f"❓ Not found in database: {not_found} accounts")
        
        if found > 0:
            insights.append(f"✅ Currently active: {active}/{found} ({active/found*100:.1f}%)")
            insights.append(f"⚠️ Currently inactive: {inactive}/{found} ({inactive/found*100:.1f}%)")
            insights.append(f"📋 Accounts with projects: {with_projects}/{found} ({with_projects/found*100:.1f}%)")
            insights.append(f"🔢 Total projects in target accounts: {total_projects}")
        
        if recent_changes:
            insights.append(f"🔄 Recent status changes (30 days): {len(recent_changes)}")
        
        # Status breakdown
        status_breakdown = status_analysis.get('status_breakdown', {})
        if status_breakdown:
            insights.append("📈 Status breakdown:")
            for status, count in status_breakdown.items():
                insights.append(f"   • {status}: {count} accounts")
        
        return insights

def main():
    """Main function for target accounts analysis"""
    print("🎯 TARGET ACCOUNTS DEEP ANALYSIS")
    print("=" * 60)
    print("These are the specific accounts that were configured with Auto Mode (1,72)")
    print(f"Total accounts to analyze: {len(TARGET_ACCOUNTS)}")
    print("This will show you exactly which accounts were changed and their current status.")
    print("=" * 60)
    print()
    
    analyzer = TargetAccountsAnalyzer()
    
    try:
        report = analyzer.generate_target_accounts_report()
        
        # Display summary
        summary = report['target_accounts_summary']
        print("📊 TARGET ACCOUNTS SUMMARY:")
        print(f"   • Total target accounts: {summary['total_target_accounts']}")
        print(f"   • Found in database: {summary['found_in_database']}")
        print(f"   • Currently active: {summary['active_accounts']}")
        print(f"   • Currently inactive: {summary['inactive_accounts']}")
        print(f"   • Not found: {summary['not_found']}")
        print(f"   • Accounts with projects: {summary['accounts_with_projects']}")
        print(f"   • Total projects: {summary['total_projects_in_target_accounts']}")
        print()
        
        # Status breakdown
        if summary.get('status_breakdown'):
            print("📈 STATUS BREAKDOWN:")
            for status, count in summary['status_breakdown'].items():
                print(f"   • {status}: {count} accounts")
            print()
        
        # Recent changes
        recent = report['recent_changes_in_targets']
        if recent:
            print(f"🔄 RECENT STATUS CHANGES (Last 30 days): {len(recent)} accounts")
            for change in recent[:10]:
                print(f"   Account {change['account_id']}: {change['account_name']}")
                print(f"      Status: {change['status']} | Projects: {change['project_count']}")
                if change['status_change_reason']:
                    print(f"      Reason: {change['status_change_reason']}")
                print(f"      Changed: {change['update_time']}")
            print()
        
        # Key insights
        print("🔍 KEY INSIGHTS:")
        for insight in report['key_insights']:
            print(f"   {insight}")
        print()
        
        # Show inactive accounts that need attention
        inactive_accounts = [acc for acc in summary['detailed_status'] if acc['status'] != 'active' and acc['project_count'] > 0]
        
        if inactive_accounts:
            print("⚠️ INACTIVE ACCOUNTS WITH PROJECTS (Need Configuration Reset):")
            for acc in inactive_accounts[:15]:
                print(f"   Account {acc['account_id']}: {acc['account_name']}")
                print(f"      Status: {acc['status']} | Projects: {acc['project_count']}")
                if acc['status_change_reason']:
                    print(f"      Reason: {acc['status_change_reason']}")
            print()
        
        # Show accounts not found
        if summary.get('not_found_accounts'):
            print(f"❓ ACCOUNTS NOT FOUND IN DATABASE ({len(summary['not_found_accounts'])}):")
            for acc_id in summary['not_found_accounts'][:10]:
                print(f"   Account ID: {acc_id}")
            if len(summary['not_found_accounts']) > 10:
                print(f"   ... and {len(summary['not_found_accounts']) - 10} more")
            print()
        
        print("=" * 60)
        print("🎯 CONFIGURATION CHANGE SUMMARY:")
        print("   • These accounts were originally configured for Auto Mode (1,72)")
        print("   • When accounts become inactive, their projects should be reset to (0,0)")
        print("   • This analysis shows which accounts changed status and need attention")
        print("   • The monitoring system should catch these changes and reset configurations")
        print()
        
        # Calculate what needs to be done
        needs_reset = len(inactive_accounts)
        total_projects_needing_reset = sum(acc['project_count'] for acc in inactive_accounts)
        
        print("🚨 ACTION NEEDED:")
        print(f"   • Inactive accounts with projects: {needs_reset}")
        print(f"   • Total projects needing reset: {total_projects_needing_reset}")
        print("   • These should be automatically detected and reset by the monitoring system")
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        print(f"❌ Analysis failed: {e}")

if __name__ == "__main__":
    main()