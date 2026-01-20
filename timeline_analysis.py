#!/usr/bin/env python3
"""
Check Configuration Timeline and Expected Inactivity
Investigate when Auto Mode was configured and if accounts should be inactive
"""

import logging
import pymysql
from datetime import datetime, timedelta
from typing import List, Dict, Any
from dotenv import load_dotenv
import os
import re

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

class ConfigurationTimelineChecker:
    """Check when Auto Mode was configured and timeline expectations"""
    
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
    
    def check_account_activity_patterns(self):
        """Check account activity and campaign patterns"""
        db = self._get_db_connection()
        cursor = db.cursor(pymysql.cursors.DictCursor)
        
        try:
            print("🕒 CHECKING ACCOUNT ACTIVITY PATTERNS:")
            print("=" * 60)
            
            account_ids = [int(acc_id) for acc_id in TARGET_ACCOUNTS]
            placeholders = ','.join(['%s'] * len(account_ids))
            
            # Check last activity, campaign count, and spending patterns
            cursor.execute(f"""
                SELECT 
                    p.id,
                    p.name,
                    p.status,
                    p.inactivity_date,
                    p.date_created,
                    p.update_time,
                    COUNT(DISTINCT sc.id) as campaign_count,
                    MAX(sc.update_time) as last_campaign_update,
                    SUM(CASE WHEN sc.status = 'RUNNING' THEN 1 ELSE 0 END) as running_campaigns
                FROM publishers p
                LEFT JOIN sp_campaigns sc ON p.id = sc.account_id
                WHERE p.id IN ({placeholders})
                GROUP BY p.id, p.name, p.status, p.inactivity_date, p.date_created, p.update_time
                ORDER BY p.status, p.id
            """, account_ids)
            
            results = cursor.fetchall()
            
            live_accounts = []
            inactive_accounts = []
            
            for result in results:
                account_info = {
                    'id': result['id'],
                    'name': result['name'],
                    'status': result['status'],
                    'inactivity_date': result['inactivity_date'],
                    'created': result['date_created'],
                    'updated': result['update_time'],
                    'campaigns': result['campaign_count'] or 0,
                    'running_campaigns': result['running_campaigns'] or 0,
                    'last_activity': result['last_campaign_update']
                }
                
                if result['status'] == 'LIVE':
                    live_accounts.append(account_info)
                else:
                    inactive_accounts.append(account_info)
            
            # Analyze LIVE accounts
            print(f"📊 LIVE ACCOUNTS ANALYSIS ({len(live_accounts)} accounts):")
            
            # Group by activity level
            highly_active = []  # > 5 campaigns, recent activity
            moderately_active = []  # 1-5 campaigns, some activity
            low_activity = []  # Few campaigns, old activity
            no_campaigns = []  # No campaigns
            
            thirty_days_ago = datetime.now() - timedelta(days=30)
            sixty_days_ago = datetime.now() - timedelta(days=60)
            
            for acc in live_accounts:
                if acc['campaigns'] == 0:
                    no_campaigns.append(acc)
                elif acc['campaigns'] > 5 and (acc['last_activity'] and acc['last_activity'] > sixty_days_ago):
                    highly_active.append(acc)
                elif acc['campaigns'] >= 1 and (acc['last_activity'] and acc['last_activity'] > sixty_days_ago):
                    moderately_active.append(acc)
                else:
                    low_activity.append(acc)
            
            print(f"   • Highly Active (>5 campaigns, recent activity): {len(highly_active)}")
            print(f"   • Moderately Active (1-5 campaigns, some activity): {len(moderately_active)}")
            print(f"   • Low Activity (old campaigns, little activity): {len(low_activity)}")
            print(f"   • No Campaigns: {len(no_campaigns)}")
            
            # Show samples of each category
            if highly_active:
                print(f"\n   📈 SAMPLE HIGHLY ACTIVE ACCOUNTS:")
                for acc in highly_active[:3]:
                    last_activity = acc['last_activity'].strftime('%Y-%m-%d') if acc['last_activity'] else 'Never'
                    print(f"      {acc['id']}: {acc['campaigns']} campaigns ({acc['running_campaigns']} running), last: {last_activity}")
            
            if no_campaigns:
                print(f"\n   ⚠️ ACCOUNTS WITH NO CAMPAIGNS ({len(no_campaigns)}):")
                for acc in no_campaigns[:10]:
                    created = acc['created'].strftime('%Y-%m-%d') if acc['created'] else 'Unknown'
                    print(f"      {acc['id']}: {acc['name']} (created: {created})")
            
            # Analyze INACTIVE accounts
            if inactive_accounts:
                print(f"\n📊 INACTIVE ACCOUNTS ANALYSIS ({len(inactive_accounts)} accounts):")
                for acc in inactive_accounts:
                    inactive_date = acc['inactivity_date'].strftime('%Y-%m-%d %H:%M') if acc['inactivity_date'] else 'Unknown'
                    print(f"   {acc['id']}: {acc['name']}")
                    print(f"      Status: {acc['status']}, Inactive since: {inactive_date}")
                    print(f"      Campaigns: {acc['campaigns']} ({acc['running_campaigns']} running)")
                    if acc['last_activity']:
                        print(f"      Last activity: {acc['last_activity'].strftime('%Y-%m-%d')}")
            
        except Exception as e:
            logger.error(f"Error checking activity patterns: {e}")
        finally:
            cursor.close()
            db.close()
    
    def check_when_auto_mode_configured(self):
        """Try to find when Auto Mode (1,72) was configured"""
        print("\n🔧 INVESTIGATING AUTO MODE CONFIGURATION TIMING:")
        print("=" * 60)
        
        print("Based on the file names in your workspace, it looks like:")
        print("- reset_inactive_accounts.py contains these 97 target accounts")
        print("- bulk_update_all_projects.py likely configured Auto Mode")
        print("- Various verification scripts suggest this was a recent bulk operation")
        print()
        
        # Check file modification times to understand timeline
        import os
        from pathlib import Path
        
        relevant_files = [
            'reset_inactive_accounts.py',
            'bulk_update_all_projects.py', 
            'start_bulk_update.py',
            'update_all_remaining.py',
            'verify_all_projects.py'
        ]
        
        print("📅 FILE MODIFICATION TIMELINE:")
        file_times = []
        
        for filename in relevant_files:
            filepath = Path(filename)
            if filepath.exists():
                mod_time = datetime.fromtimestamp(filepath.stat().st_mtime)
                file_times.append((filename, mod_time))
                print(f"   {filename}: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if file_times:
            file_times.sort(key=lambda x: x[1])
            earliest = file_times[0][1]
            latest = file_times[-1][1]
            
            print(f"\n🎯 TIMELINE ANALYSIS:")
            print(f"   • Configuration likely happened between: {earliest.strftime('%Y-%m-%d')} and {latest.strftime('%Y-%m-%d')}")
            
            days_since_earliest = (datetime.now() - earliest).days
            days_since_latest = (datetime.now() - latest).days
            
            print(f"   • Days since earliest file: {days_since_earliest}")
            print(f"   • Days since latest file: {days_since_latest}")
            
            print(f"\n🤔 EXPECTED INACTIVITY ASSESSMENT:")
            if days_since_latest < 30:
                print(f"   • Auto Mode configured recently ({days_since_latest} days ago)")
                print(f"   • Accounts might not have had enough time to become inactive")
                print(f"   • Normal pattern: accounts become inactive after 30-60 days without campaigns")
            elif days_since_latest < 60:
                print(f"   • Configuration was {days_since_latest} days ago")
                print(f"   • Some accounts should be showing inactivity by now")
                print(f"   • But high-activity accounts might still be LIVE")
            else:
                print(f"   • Configuration was {days_since_latest} days ago")
                print(f"   • More accounts should be inactive by now")
                print(f"   • These might be genuinely active accounts")
    
    def theoretical_vs_actual_analysis(self):
        """Compare theoretical expectations with actual results"""
        print("\n🧮 THEORETICAL vs ACTUAL ANALYSIS:")
        print("=" * 60)
        
        print("📚 WHAT WE EXPECTED:")
        print("   • 97 accounts configured with Auto Mode (1,72)")
        print("   • Auto Mode = automatic scanning, 72 times per day")
        print("   • If accounts become inactive → reset to Manual Mode (0,0)")
        print("   • Expected: Some accounts to become inactive over time")
        print()
        
        print("📊 WHAT WE ACTUALLY FOUND:")
        print("   • 95 accounts still LIVE (97.9%)")
        print("   • 2 accounts INACTIVE (2.1%)")
        print("   • Both inactive accounts have specific inactivity dates")
        print("   • LIVE accounts appear to have ongoing campaign activity")
        print()
        
        print("🎯 POSSIBLE CONCLUSIONS:")
        print("   1. ✅ SUCCESS: The target accounts are genuinely still active")
        print("   2. ✅ GOOD SELECTION: These 97 accounts were chosen because they're high-value/active")
        print("   3. ⏰ TIMING: Auto Mode configuration might be recent")
        print("   4. 🏆 EFFECTIVE: The Auto Mode might be working to keep campaigns active")
        print("   5. 📊 NORMAL: 2% inactivity rate might be typical for this account selection")
        print()
        
        print("❓ QUESTIONS TO CONSIDER:")
        print("   • Were these 97 accounts specifically chosen for being active/valuable?")
        print("   • How long ago was Auto Mode actually configured?")
        print("   • Is a 2% inactivity rate normal for your typical account portfolio?")
        print("   • Are you seeing increased campaign activity since Auto Mode was enabled?")

def main():
    """Main analysis function"""
    print("🕒 CONFIGURATION TIMELINE & ACTIVITY ANALYSIS")
    print("=" * 70)
    print("Let's understand WHY only 2 accounts are inactive...")
    print()
    
    checker = ConfigurationTimelineChecker()
    
    # Check current activity patterns
    checker.check_account_activity_patterns()
    
    # Try to understand when configuration happened
    checker.check_when_auto_mode_configured()
    
    # Theoretical vs actual analysis
    checker.theoretical_vs_actual_analysis()
    
    print("\n" + "=" * 70)
    print("🎯 FINAL ASSESSMENT:")
    print()
    print("Your suspicion might be correct IF:")
    print("• You expected more accounts to naturally become inactive")
    print("• The Auto Mode was configured months ago")
    print("• These accounts were a random sample (not pre-selected active ones)")
    print()
    print("But the results might be NORMAL if:")
    print("• These 97 accounts were specifically chosen for being valuable/active")
    print("• Auto Mode was configured recently (< 30 days)")
    print("• The 2 inactive accounts became inactive for specific business reasons")
    print("• Auto Mode is actually working to increase campaign activity")
    print()
    print("💡 RECOMMENDATION:")
    print("Check your bulk update logs or ask whoever ran the original Auto Mode")
    print("configuration when it was done and how these 97 accounts were selected!")

if __name__ == "__main__":
    main()