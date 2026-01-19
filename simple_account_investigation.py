#!/usr/bin/env python3
"""
Simple Account Deactivation Investigation - Fixed Version
"""
import os
import sys
import pymysql
from datetime import datetime, timedelta

def investigate_account_status():
    try:
        # Use the same environment variable approach as the main script
        from dotenv import load_dotenv
        load_dotenv()
        
        def _env_or_fail(key: str) -> str:
            value = os.getenv(key)
            if value is None:
                raise ValueError(f"Environment variable {key} is not set")
            return value
        
        # Get database connection parameters
        host = _env_or_fail("MYSQL_HOST")
        port = int(os.getenv("MYSQL_PORT", "3306"))
        user = _env_or_fail("MYSQL_USER")
        password = _env_or_fail("MYSQL_PASSWORD")
        database = _env_or_fail("MYSQL_DB")

        # Connect to database
        db = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        cursor = db.cursor(pymysql.cursors.DictCursor)
        
        print("🔍 ACCOUNT DEACTIVATION INVESTIGATION - SIMPLIFIED")
        print("=" * 60)
        
        # 1. First, let's check what fields are in publishers vs geo_edge_projects
        print("\n1️⃣ CHECKING TABLE RELATIONSHIPS:")
        print("-" * 40)
        
        cursor.execute("SHOW COLUMNS FROM publishers LIKE '%id%'")
        pub_id_cols = cursor.fetchall()
        print("Publisher ID-related columns:")
        for col in pub_id_cols:
            print(f"   • {col['Field']}: {col['Type']}")
        
        cursor.execute("SHOW COLUMNS FROM geo_edge_projects LIKE '%scan%'")
        scan_cols = cursor.fetchall()
        print("\nGeo Edge Projects scan-related columns:")
        for col in scan_cols:
            print(f"   • {col['Field']}: {col['Type']}")
        
        # Show a few more relevant columns
        cursor.execute("SHOW COLUMNS FROM geo_edge_projects")
        all_proj_cols = cursor.fetchall()
        print("\nAll geo_edge_projects columns:")
        for col in all_proj_cols:
            print(f"   • {col['Field']}: {col['Type']}")
        
        # 2. Check current status distribution
        print("\n2️⃣ CURRENT ACCOUNT STATUS DISTRIBUTION:")
        print("-" * 40)
        cursor.execute("""
            SELECT 
                status,
                COUNT(*) as count
            FROM publishers 
            GROUP BY status 
            ORDER BY count DESC
        """)
        
        status_dist = cursor.fetchall()
        for row in status_dist:
            print(f"   {row['status']: <15} {row['count']: >5} accounts")
        
        # 3. Look for accounts that became inactive recently
        print("\n3️⃣ RECENTLY INACTIVE ACCOUNTS (with update_time):")
        print("-" * 40)
        cursor.execute("""
            SELECT 
                id,
                name,
                status,
                inactivity_date,
                update_time,
                status_change_reason
            FROM publishers 
            WHERE status IN ('INACTIVE', 'inactive', 'PAUSED', 'paused', 'SUSPENDED', 'suspended')
              AND (
                  inactivity_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                  OR update_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
              )
            ORDER BY COALESCE(inactivity_date, update_time) DESC
            LIMIT 15
        """)
        
        recent_inactive = cursor.fetchall()
        print("   ID       Name                    Status      Inactive Date    Update Time")
        print("   " + "-" * 75)
        
        for row in recent_inactive:
            inactive_date = row['inactivity_date'].strftime('%Y-%m-%d') if row['inactivity_date'] else 'N/A'
            update_time = row['update_time'].strftime('%Y-%m-%d') if row['update_time'] else 'N/A'
            print(f"   {row['id']: <8} {row['name']: <23} {row['status']: <11} {inactive_date: <13} {update_time}")
        
        # 4. Check if these accounts have projects that need reset
        print("\n4️⃣ PROJECTS UNDER RECENTLY INACTIVE ACCOUNTS:")
        print("-" * 40)
        
        if recent_inactive:
            account_ids = [str(row['id']) for row in recent_inactive]
            # First let's see what columns exist and find the relationship
            cursor.execute(f"""
                SELECT 
                    p.id as publisher_id,
                    p.name as publisher_name,
                    p.status as publisher_status,
                    COUNT(g.id) as total_projects
                FROM publishers p
                LEFT JOIN geo_edge_projects g ON p.id = g.publisher_id
                WHERE p.id IN ({','.join(account_ids)})
                GROUP BY p.id, p.name, p.status
                ORDER BY total_projects DESC
                LIMIT 10
            """)
            
            projects_under_inactive = cursor.fetchall()
            print("   Pub ID   Publisher Name          Status    Total Projects")
            print("   " + "-" * 55)
            
            for row in projects_under_inactive:
                print(f"   {row['publisher_id']: <8} {row['publisher_name']: <23} {row['publisher_status']: <8} "
                      f"{row['total_projects'] or 0: >12}")
        
        # 5. Find accounts with history tables (if any exist)
        print("\n5️⃣ CHECKING FOR ACCOUNT HISTORY DATA:")
        print("-" * 40)
        
        cursor.execute("SHOW TABLES LIKE '%history%'")
        history_tables = cursor.fetchall()
        
        relevant_history = []
        for table in history_tables:
            table_name = table['Tables_in_TRC (% history%)'] if 'Tables_in_TRC (% history%)' in table else list(table.values())[0]
            if 'account' in table_name.lower() or 'publisher' in table_name.lower():
                relevant_history.append(table_name)
        
        if relevant_history:
            print("   Found relevant history tables:")
            for table in relevant_history:
                print(f"   • {table}")
                
                # Sample the history table
                try:
                    cursor.execute(f"SELECT COUNT(*) as count FROM {table} LIMIT 1")
                    count_result = cursor.fetchone()
                    print(f"     → {count_result['count']} records")
                except Exception as e:
                    print(f"     → Error accessing: {e}")
        else:
            print("   No relevant history tables found")
        
        cursor.close()
        db.close()
        
        print(f"\n✅ Investigation completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during investigation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    investigate_account_status()