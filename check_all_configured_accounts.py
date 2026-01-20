#!/usr/bin/env python3
"""
Check Status of ALL Accounts That Had Auto Mode Configuration Changed
Find all accounts that had projects configured with auto_scan=1, times_per_day=72
and check their current status
"""

import logging
import pymysql
from datetime import datetime, timedelta
from typing import List, Dict, Any, Set
from dotenv import load_dotenv
import os

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AllConfiguredAccountsChecker:
    """Find and check status of ALL accounts that had Auto Mode configured"""
    
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
    
    def find_all_configured_accounts(self):
        """Find ALL accounts that had projects configured with Auto Mode based on the bulk update criteria"""
        db = self._get_db_connection()
        cursor = db.cursor(pymysql.cursors.DictCursor)
        
        try:
            print("🔍 FINDING ALL ACCOUNTS WITH AUTO MODE CONFIGURATION:")
            print("=" * 70)
            print("Searching based on bulk_update_all_projects.py criteria:")
            print("• Projects with ACTIVE instruction status")
            print("• Projects from around October 2025 timeframe") 
            print("• Projects targeting IT/FR/DE/ES (European markets)")
            print()
            
            # Recreate the query logic from bulk_update_all_projects.py but find unique accounts
            # The original query was looking for projects from last 7 days, but since it was run in October 2025,
            # we need to look for projects created around that time targeting those countries
            
            sql = """
                SELECT DISTINCT
                    sc.syndicator_id as account_id,
                    p.name as publisher_name,
                    p.status as account_status,
                    p.inactivity_date,
                    p.update_time,
                    COUNT(DISTINCT gep.project_id) as project_count,
                    GROUP_CONCAT(DISTINCT gep.locations) as all_locations,
                    MIN(gep.creation_date) as earliest_project,
                    MAX(gep.creation_date) as latest_project
                FROM trc.geo_edge_projects AS gep
                JOIN trc.sp_campaigns sc ON gep.campaign_id = sc.id
                JOIN trc.publishers p ON sc.syndicator_id = p.id
                JOIN trc.sp_campaign_inventory_instructions sii ON gep.campaign_id = sii.campaign_id
                WHERE sii.instruction_status = 'ACTIVE'
                  AND gep.creation_date >= '2025-10-01'
                  AND gep.creation_date <= '2025-11-30'
                  AND CONCAT(',', REPLACE(COALESCE(gep.locations, ''), ' ', ''), ',') REGEXP ',(IT|FR|DE|ES),'
                GROUP BY sc.syndicator_id, p.name, p.status, p.inactivity_date, p.update_time
                ORDER BY project_count DESC, sc.syndicator_id
            """
            
            print("🔎 Executing comprehensive account search...")
            cursor.execute(sql)
            results = cursor.fetchall()
            
            print(f"✅ Found {len(results)} accounts that had Auto Mode configuration applied")
            print()
            
            # Categorize accounts by status
            live_accounts = []
            inactive_accounts = []
            other_status_accounts = []
            
            for result in results:
                account_info = {
                    'account_id': result['account_id'],
                    'publisher_name': result['publisher_name'],
                    'status': result['account_status'],
                    'inactivity_date': result['inactivity_date'],
                    'update_time': result['update_time'],
                    'project_count': result['project_count'],
                    'all_locations': result['all_locations'],
                    'earliest_project': result['earliest_project'],
                    'latest_project': result['latest_project']
                }
                
                if result['account_status'] == 'LIVE':
                    live_accounts.append(account_info)
                elif result['account_status'] == 'INACTIVE':
                    inactive_accounts.append(account_info)
                else:
                    other_status_accounts.append(account_info)
            
            # Display summary
            print("📊 ACCOUNT STATUS SUMMARY:")
            print(f"   • LIVE accounts: {len(live_accounts)} ({(len(live_accounts)/len(results)*100):.1f}%)")
            print(f"   • INACTIVE accounts: {len(inactive_accounts)} ({(len(inactive_accounts)/len(results)*100):.1f}%)")
            print(f"   • Other status accounts: {len(other_status_accounts)} ({(len(other_status_accounts)/len(results)*100):.1f}%)")
            print(f"   • Total configured accounts: {len(results)}")
            print()
            
            return {
                'live_accounts': live_accounts,
                'inactive_accounts': inactive_accounts,
                'other_status_accounts': other_status_accounts,
                'total_accounts': len(results)
            }
            
        except Exception as e:
            logger.error(f"Error finding configured accounts: {e}")
            return None
        finally:
            cursor.close()
            db.close()
    
    def analyze_inactive_accounts(self, inactive_accounts):
        """Analyze the inactive accounts in detail"""
        if not inactive_accounts:
            print("✅ No inactive accounts found!")
            return
        
        print("🚨 DETAILED ANALYSIS OF INACTIVE ACCOUNTS:")
        print("=" * 70)
        
        # Sort by inactivity date
        inactive_accounts.sort(key=lambda x: x['inactivity_date'] if x['inactivity_date'] else datetime.min)
        
        print(f"Found {len(inactive_accounts)} inactive accounts:")
        print()
        
        for i, account in enumerate(inactive_accounts, 1):
            inactive_date = account['inactivity_date'].strftime('%Y-%m-%d %H:%M:%S') if account['inactivity_date'] else 'Unknown'
            update_date = account['update_time'].strftime('%Y-%m-%d %H:%M:%S') if account['update_time'] else 'Unknown'
            earliest_proj = account['earliest_project'].strftime('%Y-%m-%d') if account['earliest_project'] else 'Unknown'
            latest_proj = account['latest_project'].strftime('%Y-%m-%d') if account['latest_project'] else 'Unknown'
            
            print(f"   {i}. Account ID: {account['account_id']}")
            print(f"      Name: {account['publisher_name']}")
            print(f"      Status: {account['status']}")
            print(f"      Projects: {account['project_count']} projects")
            print(f"      Locations: {account['all_locations']}")
            print(f"      Inactive since: {inactive_date}")
            print(f"      Last update: {update_date}")
            print(f"      Project dates: {earliest_proj} to {latest_proj}")
            print()
        
        # Check how many were in the original 97 target accounts
        target_accounts_set = {
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
        }
        
        target_inactive = []
        new_inactive = []
        
        for account in inactive_accounts:
            if str(account['account_id']) in target_accounts_set:
                target_inactive.append(account)
            else:
                new_inactive.append(account)
        
        print("🎯 INACTIVE ACCOUNT BREAKDOWN:")
        print(f"   • Inactive accounts from original 97 targets: {len(target_inactive)}")
        print(f"   • NEW inactive accounts discovered: {len(new_inactive)}")
        
        if new_inactive:
            print(f"\n🆕 NEWLY DISCOVERED INACTIVE ACCOUNTS:")
            for account in new_inactive:
                print(f"   • Account {account['account_id']}: {account['publisher_name']}")
    
    def compare_with_target_accounts(self, all_configured):
        """Compare findings with the original 97 target accounts"""
        print("\n🔄 COMPARISON WITH ORIGINAL 97 TARGET ACCOUNTS:")
        print("=" * 70)
        
        # Target accounts from reset_inactive_accounts.py
        target_accounts_set = {
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
        }
        
        # Get all configured account IDs
        all_configured_ids = set()
        for status_group in ['live_accounts', 'inactive_accounts', 'other_status_accounts']:
            for account in all_configured[status_group]:
                all_configured_ids.add(str(account['account_id']))
        
        # Find overlaps and differences
        in_both = target_accounts_set.intersection(all_configured_ids)
        only_in_targets = target_accounts_set - all_configured_ids
        only_in_configured = all_configured_ids - target_accounts_set
        
        print(f"📊 ACCOUNT SET COMPARISON:")
        print(f"   • Original target accounts: {len(target_accounts_set)}")
        print(f"   • Actually configured accounts: {len(all_configured_ids)}")
        print(f"   • Accounts in both sets: {len(in_both)}")
        print(f"   • Only in target list: {len(only_in_targets)}")
        print(f"   • Only in configured list: {len(only_in_configured)}")
        
        if only_in_targets:
            print(f"\n❓ ACCOUNTS IN TARGET LIST BUT NOT FOUND IN CONFIGURED:")
            print("   (These might not have had projects matching the criteria)")
            for acc_id in sorted(only_in_targets)[:10]:  # Show first 10
                print(f"   • Account {acc_id}")
            if len(only_in_targets) > 10:
                print(f"   ... and {len(only_in_targets) - 10} more")
        
        if only_in_configured:
            print(f"\n🆕 ADDITIONAL ACCOUNTS FOUND BEYOND TARGET LIST:")
            print("   (These had Auto Mode configured but weren't in the monitoring list)")
            for acc_id in sorted(only_in_configured)[:10]:  # Show first 10
                print(f"   • Account {acc_id}")
            if len(only_in_configured) > 10:
                print(f"   ... and {len(only_in_configured) - 10} more")

def main():
    """Main function to check all configured accounts"""
    print("🔍 COMPREHENSIVE ANALYSIS: ALL ACCOUNTS WITH AUTO MODE CONFIGURATION")
    print("=" * 80)
    print("Finding ALL accounts that had their configuration changed to Auto Mode (1,72)")
    print("not just the 97 accounts in the monitoring target list...")
    print()
    
    checker = AllConfiguredAccountsChecker()
    
    # Find all configured accounts
    all_configured = checker.find_all_configured_accounts()
    
    if all_configured:
        # Analyze inactive accounts
        checker.analyze_inactive_accounts(all_configured['inactive_accounts'])
        
        # Compare with original target accounts
        checker.compare_with_target_accounts(all_configured)
        
        print("\n" + "=" * 80)
        print("🎯 FINAL SUMMARY:")
        print(f"   • Total accounts with Auto Mode configuration: {all_configured['total_accounts']}")
        print(f"   • LIVE accounts: {len(all_configured['live_accounts'])}")
        print(f"   • INACTIVE accounts: {len(all_configured['inactive_accounts'])}")
        print(f"   • Other status: {len(all_configured['other_status_accounts'])}")
        
        if all_configured['inactive_accounts']:
            inactivity_rate = (len(all_configured['inactive_accounts']) / all_configured['total_accounts']) * 100
            print(f"   • Inactivity rate: {inactivity_rate:.1f}%")
        
        print("=" * 80)

if __name__ == "__main__":
    main()