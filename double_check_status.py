#!/usr/bin/env python3
"""
Double-Check Target Accounts Status Analysis
More detailed investigation of account statuses
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

# Target accounts from reset_inactive_accounts.py
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

class DetailedStatusChecker:
    """Detailed status verification for target accounts"""
    
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
    
    def check_all_possible_statuses(self):
        """Check what status values actually exist in the database"""
        db = self._get_db_connection()
        cursor = db.cursor(pymysql.cursors.DictCursor)
        
        try:
            print("🔍 INVESTIGATING ALL STATUS VALUES IN DATABASE:")
            print("=" * 60)
            
            # Get all unique status values
            cursor.execute("SELECT DISTINCT status, COUNT(*) as count FROM publishers GROUP BY status ORDER BY count DESC")
            all_statuses = cursor.fetchall()
            
            print("📊 ALL STATUS VALUES IN PUBLISHERS TABLE:")
            for status in all_statuses:
                print(f"   • '{status['status']}': {status['count']} accounts")
            
            return all_statuses
            
        except Exception as e:
            logger.error(f"Error checking statuses: {e}")
            return []
        finally:
            cursor.close()
            db.close()
    
    def detailed_target_account_check(self):
        """Detailed check of each target account individually"""
        db = self._get_db_connection()
        cursor = db.cursor(pymysql.cursors.DictCursor)
        
        detailed_results = {
            'accounts_checked': 0,
            'accounts_found': 0,
            'accounts_not_found': [],
            'status_counts': {},
            'detailed_accounts': []
        }
        
        try:
            print("\n🎯 DETAILED TARGET ACCOUNT STATUS CHECK:")
            print("=" * 60)
            
            for acc_id in TARGET_ACCOUNTS:
                try:
                    cursor.execute("""
                        SELECT 
                            id,
                            name,
                            status,
                            status_change_reason,
                            status_change_performer,
                            update_time,
                            inactivity_date,
                            date_created
                        FROM publishers 
                        WHERE id = %s
                    """, (int(acc_id),))
                    
                    result = cursor.fetchone()
                    detailed_results['accounts_checked'] += 1
                    
                    if result:
                        detailed_results['accounts_found'] += 1
                        
                        status = result['status']
                        if status in detailed_results['status_counts']:
                            detailed_results['status_counts'][status] += 1
                        else:
                            detailed_results['status_counts'][status] = 1
                        
                        account_detail = {
                            'id': acc_id,
                            'name': result['name'],
                            'status': result['status'],
                            'status_change_reason': result['status_change_reason'],
                            'status_change_performer': result['status_change_performer'],
                            'update_time': result['update_time'].isoformat() if result['update_time'] else None,
                            'inactivity_date': result['inactivity_date'].isoformat() if result['inactivity_date'] else None,
                            'date_created': result['date_created'].isoformat() if result['date_created'] else None
                        }
                        
                        detailed_results['detailed_accounts'].append(account_detail)
                        
                    else:
                        detailed_results['accounts_not_found'].append(acc_id)
                        print(f"❌ Account {acc_id}: NOT FOUND in database")
                        
                except Exception as e:
                    logger.error(f"Error checking account {acc_id}: {e}")
                    detailed_results['accounts_not_found'].append(acc_id)
            
            # Print summary
            print(f"\n📊 TARGET ACCOUNT STATUS SUMMARY:")
            print(f"   • Accounts checked: {detailed_results['accounts_checked']}")
            print(f"   • Accounts found: {detailed_results['accounts_found']}")
            print(f"   • Accounts not found: {len(detailed_results['accounts_not_found'])}")
            
            print(f"\n📈 STATUS BREAKDOWN FOR TARGET ACCOUNTS:")
            for status, count in detailed_results['status_counts'].items():
                percentage = (count / detailed_results['accounts_found']) * 100 if detailed_results['accounts_found'] > 0 else 0
                print(f"   • '{status}': {count} accounts ({percentage:.1f}%)")
            
            return detailed_results
            
        except Exception as e:
            logger.error(f"Error in detailed check: {e}")
            return detailed_results
        finally:
            cursor.close()
            db.close()
    
    def check_what_inactive_means(self):
        """Check what different status values might mean 'inactive'"""
        db = self._get_db_connection()
        cursor = db.cursor(pymysql.cursors.DictCursor)
        
        try:
            print("\n🔍 CHECKING WHAT STATUSES MIGHT MEAN 'INACTIVE':")
            print("=" * 60)
            
            # Check target accounts with various status conditions
            account_ids = [int(acc_id) for acc_id in TARGET_ACCOUNTS]
            placeholders = ','.join(['%s'] * len(account_ids))
            
            # Check different potential "inactive" conditions
            conditions = {
                "status != 'LIVE'": f"status != 'LIVE'",
                "status = 'INACTIVE'": f"status = 'INACTIVE'", 
                "status = 'PAUSED'": f"status = 'PAUSED'",
                "status = 'SUSPENDED'": f"status = 'SUSPENDED'",
                "status = 'FROZEN'": f"status = 'FROZEN'",
                "status IN ('INACTIVE', 'PAUSED', 'SUSPENDED', 'FROZEN')": f"status IN ('INACTIVE', 'PAUSED', 'SUSPENDED', 'FROZEN')",
                "inactivity_date IS NOT NULL": f"inactivity_date IS NOT NULL"
            }
            
            for condition_name, condition_sql in conditions.items():
                cursor.execute(f"""
                    SELECT COUNT(*) as count, GROUP_CONCAT(DISTINCT status) as statuses
                    FROM publishers 
                    WHERE id IN ({placeholders}) 
                    AND {condition_sql}
                """, account_ids)
                
                result = cursor.fetchone()
                print(f"   • {condition_name}: {result['count']} accounts")
                if result['statuses']:
                    print(f"     Statuses: {result['statuses']}")
            
            # Show some examples of each status
            print(f"\n📋 SAMPLE ACCOUNTS BY STATUS:")
            cursor.execute(f"""
                SELECT status, id, name, inactivity_date, status_change_reason
                FROM publishers 
                WHERE id IN ({placeholders})
                ORDER BY status, id
            """, account_ids)
            
            results = cursor.fetchall()
            current_status = None
            count = 0
            
            for result in results:
                if result['status'] != current_status:
                    current_status = result['status']
                    count = 0
                    print(f"\n   Status '{current_status}':")
                
                if count < 3:  # Show first 3 examples of each status
                    inactivity_str = f" (inactive: {result['inactivity_date']})" if result['inactivity_date'] else ""
                    reason_str = f" - Reason: {result['status_change_reason']}" if result['status_change_reason'] else ""
                    print(f"      Account {result['id']}: {result['name']}{inactivity_str}{reason_str}")
                count += 1
            
        except Exception as e:
            logger.error(f"Error checking inactive conditions: {e}")
        finally:
            cursor.close()
            db.close()

def main():
    """Main double-check function"""
    print("🔍 DOUBLE-CHECKING TARGET ACCOUNT STATUSES")
    print("=" * 70)
    print("You're right to question this! Let's investigate more thoroughly...")
    print()
    
    checker = DetailedStatusChecker()
    
    # Check all possible statuses in database
    all_statuses = checker.check_all_possible_statuses()
    
    # Detailed check of target accounts
    detailed_results = checker.detailed_target_account_check()
    
    # Check what might mean "inactive"
    checker.check_what_inactive_means()
    
    print("\n" + "=" * 70)
    print("🎯 DOUBLE-CHECK CONCLUSIONS:")
    print()
    
    if detailed_results['accounts_found'] > 0:
        print(f"✅ Found {detailed_results['accounts_found']}/{len(TARGET_ACCOUNTS)} target accounts")
        
        # Analyze what we found
        total_found = detailed_results['accounts_found']
        status_counts = detailed_results['status_counts']
        
        live_count = status_counts.get('LIVE', 0)
        inactive_count = status_counts.get('INACTIVE', 0)
        
        print(f"📊 Status breakdown:")
        for status, count in status_counts.items():
            percentage = (count / total_found) * 100
            print(f"   • {status}: {count} accounts ({percentage:.1f}%)")
        
        # Check if our previous analysis was correct
        if live_count > 0 and inactive_count < 10:
            print(f"\n🤔 ANALYSIS:")
            print(f"   • Previous analysis showed: LIVE={live_count}, INACTIVE={inactive_count}")
            print(f"   • This might be correct if most accounts are actually still LIVE")
            print(f"   • However, you expected more inactive accounts...")
            print(f"   • Possible reasons:")
            print(f"     - These accounts haven't actually become inactive yet")
            print(f"     - The accounts are still being actively used")
            print(f"     - 'LIVE' might be the normal active status")
            print(f"     - We might need to check different criteria for 'inactive'")
        
        # Show accounts with inactivity dates
        accounts_with_inactivity = [acc for acc in detailed_results['detailed_accounts'] if acc['inactivity_date']]
        if accounts_with_inactivity:
            print(f"\n⚠️ ACCOUNTS WITH INACTIVITY DATES ({len(accounts_with_inactivity)}):")
            for acc in accounts_with_inactivity[:10]:
                print(f"   Account {acc['id']}: {acc['name']} - Status: {acc['status']}, Inactive: {acc['inactivity_date']}")
        
        # Show recent status changes
        recent_changes = [acc for acc in detailed_results['detailed_accounts'] 
                         if acc['update_time'] and acc['update_time'] > '2025-12-01']
        if recent_changes:
            print(f"\n🔄 RECENT STATUS CHANGES ({len(recent_changes)}):")
            for acc in recent_changes[:10]:
                print(f"   Account {acc['id']}: {acc['name']} - Status: {acc['status']}, Updated: {acc['update_time']}")
                if acc['status_change_reason']:
                    print(f"      Reason: {acc['status_change_reason']}")
    
    print(f"\n❓ POSSIBLE EXPLANATIONS:")
    print(f"   1. Most target accounts are still actively being used (hence LIVE status)")
    print(f"   2. 'LIVE' might be the equivalent of 'active' in this database")
    print(f"   3. Accounts might not have become inactive as expected")
    print(f"   4. The definition of 'inactive' might be different than expected")
    print(f"   5. These specific accounts might be high-value and kept active")

if __name__ == "__main__":
    main()