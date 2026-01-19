#!/usr/bin/env python3
"""
Account Status Change Detection for GeoEdge Reset System

This script helps identify when accounts became inactive and ensures
all projects under newly inactive accounts are immediately set to (0,0).
"""

import os
import sys
import pymysql
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    """Create database connection"""
    return pymysql.connect(
        host=os.getenv('MYSQL_HOST'),
        port=int(os.getenv('MYSQL_PORT', 3306)),
        user=os.getenv('MYSQL_USER'),
        password=os.getenv('MYSQL_PASSWORD'),
        database=os.getenv('MYSQL_DB'),
        cursorclass=pymysql.cursors.DictCursor
    )

def find_account_deactivation_indicators():
    """
    Find various indicators of when accounts might have been deactivated.
    This explores different approaches since there might not be a direct timestamp.
    """
    
    print("🔍 Searching for account deactivation indicators...\n")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Query 1: Check for any timestamp fields in publishers table
        print("1️⃣ Checking publishers table structure for timestamp fields:")
        cursor.execute("DESCRIBE publishers")
        columns = cursor.fetchall()
        timestamp_columns = []
        
        for col in columns:
            col_name = col['Field'].lower()
            if any(keyword in col_name for keyword in ['date', 'time', 'created', 'updated', 'modified', 'last']):
                timestamp_columns.append(col['Field'])
                print(f"   📅 Found: {col['Field']} ({col['Type']})")
        
        if not timestamp_columns:
            print("   ❌ No obvious timestamp columns found")
        
        # Query 2: Check for recent status changes (if we have timestamp fields)
        if timestamp_columns:
            print(f"\n2️⃣ Checking for recent changes in publishers table:")
            
            # Try to find accounts that might have changed status recently
            for ts_col in timestamp_columns[:2]:  # Check first 2 timestamp columns
                try:
                    query = f"""
                    SELECT syndicator_id, status, {ts_col} as timestamp_field
                    FROM publishers 
                    WHERE {ts_col} >= DATE_SUB(NOW(), INTERVAL 7 DAYS)
                    AND status IN ('inactive', 'paused', 'suspended', 'frozen')
                    ORDER BY {ts_col} DESC
                    LIMIT 10
                    """
                    cursor.execute(query)
                    recent_changes = cursor.fetchall()
                    
                    if recent_changes:
                        print(f"   📊 Recent status changes (using {ts_col}):")
                        for row in recent_changes:
                            print(f"      Account {row['syndicator_id']}: {row['status']} at {row['timestamp_field']}")
                    else:
                        print(f"   ➖ No recent changes found using {ts_col}")
                except Exception as e:
                    print(f"   ⚠️ Error checking {ts_col}: {e}")
        
        # Query 3: Check for activity-based indicators
        print(f"\n3️⃣ Checking activity-based deactivation indicators:")
        
        # Last campaign creation dates
        try:
            cursor.execute("""
            SELECT p.syndicator_id, p.status, 
                   MAX(sp.date_created) as last_campaign_created,
                   COUNT(sp.id) as total_campaigns
            FROM publishers p
            LEFT JOIN sp_campaigns sp ON p.syndicator_id = sp.syndicator_id
            WHERE p.status IN ('inactive', 'paused', 'suspended', 'frozen')
            GROUP BY p.syndicator_id, p.status
            HAVING last_campaign_created IS NOT NULL
            ORDER BY last_campaign_created DESC
            LIMIT 10
            """)
            
            activity_data = cursor.fetchall()
            if activity_data:
                print("   📈 Last campaign activity for inactive accounts:")
                for row in activity_data:
                    days_since = (datetime.now() - row['last_campaign_created']).days if row['last_campaign_created'] else None
                    print(f"      Account {row['syndicator_id']}: Last campaign {days_since} days ago ({row['total_campaigns']} total)")
            else:
                print("   ❌ No campaign activity data found")
                
        except Exception as e:
            print(f"   ⚠️ Error checking campaign activity: {e}")
        
        # Query 4: Look for accounts with projects but inactive status (potential recent changes)
        print(f"\n4️⃣ Checking for inactive accounts with recent projects:")
        
        try:
            cursor.execute("""
            SELECT p.syndicator_id, p.status,
                   COUNT(gep.project_id) as project_count,
                   MAX(gep.date_created) as latest_project
            FROM publishers p
            JOIN geo_edge_projects gep ON p.syndicator_id = gep.syndicator_id
            WHERE p.status IN ('inactive', 'paused', 'suspended', 'frozen')
            AND gep.date_created >= DATE_SUB(NOW(), INTERVAL 30 DAYS)
            GROUP BY p.syndicator_id, p.status
            ORDER BY latest_project DESC
            LIMIT 10
            """)
            
            recent_projects = cursor.fetchall()
            if recent_projects:
                print("   🚨 ALERT: Inactive accounts with recent projects (possible recent deactivation):")
                for row in recent_projects:
                    days_since = (datetime.now() - row['latest_project']).days if row['latest_project'] else None
                    print(f"      🔴 Account {row['syndicator_id']} ({row['status']}): {row['project_count']} projects, latest {days_since} days ago")
            else:
                print("   ✅ No inactive accounts with recent projects found")
                
        except Exception as e:
            print(f"   ⚠️ Error checking recent projects: {e}")

def check_newly_inactive_accounts(hours_back: int = 24):
    """
    Try to identify accounts that became inactive in the specified timeframe.
    Uses multiple heuristics since direct timestamp tracking might not be available.
    """
    
    print(f"\n🕐 Checking for accounts that became inactive in last {hours_back} hours...\n")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Strategy 1: Use audit/log tables if they exist
        audit_tables = ['publishers_audit', 'account_status_log', 'publishers_history']
        
        for table in audit_tables:
            try:
                cursor.execute(f"SHOW TABLES LIKE '{table}'")
                if cursor.fetchone():
                    print(f"📋 Found audit table: {table}")
                    cursor.execute(f"DESCRIBE {table}")
                    print("   Columns:", [col['Field'] for col in cursor.fetchall()])
                    # Add specific queries for audit tables here
            except:
                pass
        
        # Strategy 2: Compare with previous known active accounts
        print("📊 Generating baseline for future comparisons...")
        
        # Create a query to establish current status baseline
        cursor.execute("""
        SELECT syndicator_id, status, 
               COUNT(*) as project_count
        FROM publishers p
        LEFT JOIN geo_edge_projects gep ON p.syndicator_id = gep.syndicator_id
        WHERE p.syndicator_id IN (
            SELECT DISTINCT syndicator_id 
            FROM geo_edge_projects 
            WHERE date_created >= DATE_SUB(NOW(), INTERVAL 90 DAYS)
        )
        GROUP BY syndicator_id, status
        ORDER BY status, syndicator_id
        """)
        
        current_status = cursor.fetchall()
        
        # Save this as a baseline file for future comparisons
        baseline_file = f"account_status_baseline_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
        
        with open(baseline_file, 'w') as f:
            f.write(f"# Account Status Baseline - {datetime.now()}\n")
            f.write("# Format: account_id,status,project_count\n")
            
            active_count = 0
            inactive_count = 0
            
            for row in current_status:
                f.write(f"{row['syndicator_id']},{row['status']},{row['project_count'] or 0}\n")
                if row['status'] in ['inactive', 'paused', 'suspended', 'frozen']:
                    inactive_count += 1
                else:
                    active_count += 1
        
        print(f"✅ Baseline saved to: {baseline_file}")
        print(f"   📊 Active accounts: {active_count}")
        print(f"   📊 Inactive accounts: {inactive_count}")
        
        return current_status

def enhanced_reset_for_status_changes():
    """
    Enhanced reset logic that detects and handles newly inactive accounts.
    This compares current status with previous baseline.
    """
    
    print("\n🔄 Enhanced Reset Logic for Status Changes\n")
    
    # Look for previous baseline files
    import glob
    baseline_files = sorted(glob.glob("account_status_baseline_*.txt"), reverse=True)
    
    if not baseline_files:
        print("❌ No previous baseline found. Run check_newly_inactive_accounts() first.")
        return []
    
    print(f"📋 Using previous baseline: {baseline_files[0]}")
    
    # Load previous status
    previous_status = {}
    with open(baseline_files[0], 'r') as f:
        for line in f:
            if line.startswith('#'):
                continue
            parts = line.strip().split(',')
            if len(parts) >= 2:
                account_id, status = parts[0], parts[1]
                previous_status[account_id] = status
    
    # Get current status
    current_status = {}
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT syndicator_id, status
        FROM publishers 
        WHERE syndicator_id IN (
            SELECT DISTINCT syndicator_id 
            FROM geo_edge_projects 
            WHERE date_created >= DATE_SUB(NOW(), INTERVAL 90 DAYS)
        )
        """)
        
        for row in cursor.fetchall():
            current_status[str(row['syndicator_id'])] = row['status']
    
    # Find accounts that changed to inactive
    newly_inactive = []
    status_changes = []
    
    for account_id, current_stat in current_status.items():
        previous_stat = previous_status.get(account_id, 'unknown')
        
        if current_stat != previous_stat:
            status_changes.append({
                'account_id': account_id,
                'previous_status': previous_stat,
                'current_status': current_stat
            })
            
            # Check if became inactive
            if (previous_stat not in ['inactive', 'paused', 'suspended', 'frozen'] and 
                current_stat in ['inactive', 'paused', 'suspended', 'frozen']):
                newly_inactive.append(account_id)
    
    if status_changes:
        print("🔄 Status Changes Detected:")
        for change in status_changes:
            icon = "🔴" if change['current_status'] in ['inactive', 'paused', 'suspended', 'frozen'] else "🟢"
            print(f"   {icon} Account {change['account_id']}: {change['previous_status']} → {change['current_status']}")
    
    if newly_inactive:
        print(f"\n🚨 NEWLY INACTIVE ACCOUNTS FOUND: {len(newly_inactive)}")
        for account_id in newly_inactive:
            print(f"   🔴 Account {account_id} became inactive")
        
        print(f"\n⚡ These accounts need IMMEDIATE project reset to (0,0)")
        return newly_inactive
    else:
        print("✅ No newly inactive accounts detected")
        return []

def main():
    """Main function to run account deactivation analysis"""
    
    print("🔍 GeoEdge Account Deactivation Detective")
    print("=" * 50)
    
    try:
        # Step 1: Explore deactivation indicators
        find_account_deactivation_indicators()
        
        # Step 2: Check for newly inactive accounts
        current_status = check_newly_inactive_accounts()
        
        # Step 3: Enhanced reset logic
        newly_inactive = enhanced_reset_for_status_changes()
        
        # Step 4: Recommendations
        print("\n" + "=" * 50)
        print("📋 RECOMMENDATIONS:")
        print()
        
        if newly_inactive:
            print("🚨 IMMEDIATE ACTION REQUIRED:")
            print(f"   • {len(newly_inactive)} accounts became inactive")
            print("   • Run reset script with these specific accounts")
            print("   • Set all their projects to Manual Mode (0,0)")
        
        print("🔄 PROCESS IMPROVEMENTS:")
        print("   • Baseline files are now created for status change tracking")
        print("   • Run this script daily before the main reset script")
        print("   • Consider adding status change alerting")
        print("   • Monitor accounts with recent projects but inactive status")
        
        return newly_inactive
        
    except Exception as e:
        print(f"❌ Error in analysis: {e}")
        return []

if __name__ == "__main__":
    newly_inactive_accounts = main()