#!/usr/bin/env python3
"""
Account Deactivation Analysis Tool - Proper Relationships
"""
import os
import sys
import pymysql
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

def _env_or_fail(key: str) -> str:
    value = os.getenv(key)
    if value is None:
        raise ValueError(f"Environment variable {key} is not set")
    return value

def analyze_account_deactivation():
    try:
        # Database connection
        host = _env_or_fail("MYSQL_HOST")
        port = int(os.getenv("MYSQL_PORT", "3306"))
        user = _env_or_fail("MYSQL_USER")
        password = _env_or_fail("MYSQL_PASSWORD")
        database = _env_or_fail("MYSQL_DB")

        db = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        
        cursor = db.cursor()
        
        print("🔍 ACCOUNT DEACTIVATION ANALYSIS")
        print("=" * 60)
        
        # 1. Find accounts that became inactive in last 24 hours
        print("\n1️⃣ ACCOUNTS THAT BECAME INACTIVE IN LAST 24 HOURS:")
        print("-" * 50)
        cursor.execute("""
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
            ORDER BY COALESCE(inactivity_date, update_time) DESC
        """)
        
        recent_inactive = cursor.fetchall()
        if recent_inactive:
            print("   Publisher ID  Name                         Hours Ago  Change Reason")
            print("   " + "-" * 75)
            for row in recent_inactive:
                reason = (row['status_change_reason'] or 'Not specified')[:30]
                print(f"   {row['publisher_id']: <12} {row['publisher_name']: <28} {row['hours_ago']: >9} {reason}")
        else:
            print("   ✅ No accounts became inactive in the last 24 hours")
        
        # 2. Find projects under these recently inactive accounts
        print("\n2️⃣ PROJECTS UNDER RECENTLY INACTIVE ACCOUNTS:")
        print("-" * 50)
        
        if recent_inactive:
            inactive_ids = [str(row['publisher_id']) for row in recent_inactive]
            
            cursor.execute(f"""
                SELECT 
                    p.id as publisher_id,
                    p.name as publisher_name,
                    p.status as publisher_status,
                    COUNT(DISTINCT gep.project_id) as total_projects,
                    COUNT(DISTINCT c.id) as total_campaigns,
                    MAX(gep.creation_date) as latest_project_date,
                    COUNT(CASE WHEN c.status = 'ACTIVE' THEN 1 END) as active_campaigns
                FROM publishers p
                LEFT JOIN sp_campaigns c ON p.id = c.syndicator_id
                LEFT JOIN geo_edge_projects gep ON c.id = gep.campaign_id
                WHERE p.id IN ({','.join(inactive_ids)})
                GROUP BY p.id, p.name, p.status
                ORDER BY total_projects DESC
            """)
            
            projects_data = cursor.fetchall()
            print("   Pub ID     Name                   Status    Projects  Campaigns  Active Camps")
            print("   " + "-" * 75)
            
            total_projects_need_reset = 0
            for row in projects_data:
                total_projects_need_reset += row['total_projects'] or 0
                print(f"   {row['publisher_id']: <10} {row['publisher_name']: <22} {row['publisher_status']: <8} "
                      f"{row['total_projects'] or 0: >8} {row['total_campaigns'] or 0: >9} {row['active_campaigns'] or 0: >11}")
            
            print(f"\n   🎯 TOTAL PROJECTS NEEDING RESET: {total_projects_need_reset}")
        
        # 3. Check for account status changes using history tables
        print("\n3️⃣ CHECKING ACCOUNT HISTORY FOR STATUS CHANGES:")
        print("-" * 50)
        
        # Check if account_history table exists and has recent changes
        cursor.execute("SHOW TABLES LIKE 'account_history'")
        if cursor.fetchone():
            cursor.execute("""
                SELECT 
                    object_id as publisher_id,
                    old_value,
                    new_value,
                    change_time,
                    TIMESTAMPDIFF(HOUR, change_time, NOW()) as hours_ago
                FROM account_history 
                WHERE field_name = 'status'
                  AND new_value = 'INACTIVE'
                  AND change_time >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
                ORDER BY change_time DESC
                LIMIT 10
            """)
            
            history_changes = cursor.fetchall()
            if history_changes:
                print("   Publisher ID  Old Status  New Status  Hours Ago")
                print("   " + "-" * 50)
                for row in history_changes:
                    print(f"   {row['publisher_id']: <12} {row['old_value']: <10} {row['new_value']: <10} {row['hours_ago']: >9}")
            else:
                print("   No recent status changes found in account_history")
        else:
            print("   account_history table not found")
        
        # 4. Query to identify when accounts were deactivated
        print("\n4️⃣ SQL QUERIES FOR ACCOUNT DEACTIVATION INVESTIGATION:")
        print("-" * 50)
        
        print("""
   📋 Manual Query for Account Deactivation Investigation:
   
   -- Find accounts deactivated in last 24 hours:
   SELECT 
       id as publisher_id,
       name,
       status,
       inactivity_date,
       update_time,
       status_change_reason,
       TIMESTAMPDIFF(HOUR, COALESCE(inactivity_date, update_time), NOW()) as hours_ago
   FROM publishers 
   WHERE status = 'INACTIVE'
     AND (inactivity_date >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
          OR (inactivity_date IS NULL AND update_time >= DATE_SUB(NOW(), INTERVAL 24 HOUR)))
   ORDER BY COALESCE(inactivity_date, update_time) DESC;
   
   -- Check projects under specific account:
   SELECT 
       gep.project_id,
       gep.creation_date,
       c.syndicator_id,
       c.status as campaign_status
   FROM geo_edge_projects gep
   JOIN sp_campaigns c ON gep.campaign_id = c.id
   WHERE c.syndicator_id = 'ACCOUNT_ID_HERE';
   
   -- Count projects needing reset for an account:
   SELECT 
       c.syndicator_id,
       COUNT(DISTINCT gep.project_id) as total_projects
   FROM sp_campaigns c
   LEFT JOIN geo_edge_projects gep ON c.id = gep.campaign_id
   WHERE c.syndicator_id = 'ACCOUNT_ID_HERE'
   GROUP BY c.syndicator_id;
   """)
        
        # 5. Create baseline for future comparisons
        print("\n5️⃣ CREATING BASELINE FOR FUTURE COMPARISONS:")
        print("-" * 50)
        
        # Get current snapshot of account statuses
        cursor.execute("""
            SELECT 
                id,
                name,
                status,
                update_time
            FROM publishers 
            WHERE status IN ('LIVE', 'ACTIVE', 'INACTIVE')
            ORDER BY id
        """)
        
        all_accounts = cursor.fetchall()
        
        # Write baseline file
        baseline_file = "/tmp/account_status_baseline.txt"
        with open(baseline_file, 'w') as f:
            f.write(f"# Account Status Baseline - {datetime.now()}\n")
            for acc in all_accounts:
                f.write(f"{acc['id']}|{acc['status']}|{acc['update_time']}\n")
        
        print(f"   ✅ Baseline created: {baseline_file}")
        print(f"   📊 Total accounts in baseline: {len(all_accounts)}")
        print(f"   🔍 Use this baseline to detect newly inactive accounts in future runs")
        
        cursor.close()
        db.close()
        
        print(f"\n✅ Analysis completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_account_deactivation()