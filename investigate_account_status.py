#!/usr/bin/env python3
"""
Database Investigation Script for Account Deactivation Timing

This script provides specific queries to help understand when and why accounts become inactive.
"""

import os
import pymysql
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

def run_investigation_queries():
    """Run comprehensive queries to understand account deactivation patterns"""
    
    print("🔍 GEOEDGE ACCOUNT DEACTIVATION INVESTIGATION")
    print("=" * 60)
    
    with pymysql.connect(
        host=os.getenv('MYSQL_HOST'),
        port=int(os.getenv('MYSQL_PORT', 3306)),
        user=os.getenv('MYSQL_USER'),
        password=os.getenv('MYSQL_PASSWORD'),
        database=os.getenv('MYSQL_DB'),
        cursorclass=pymysql.cursors.DictCursor
    ) as conn:
        
        cursor = conn.cursor()
        
        print("\n1️⃣ EXPLORING DATABASE SCHEMA:")
        print("-" * 40)
        
        # Check what tables might have audit/history information
        cursor.execute("SHOW TABLES")
        all_tables = [row[f'Tables_in_{os.getenv("MYSQL_DB")}'] for row in cursor.fetchall()]
        
        audit_related = [t for t in all_tables if any(word in t.lower() for word in ['audit', 'log', 'history', 'change'])]
        if audit_related:
            print("📋 Found potential audit tables:")
            for table in audit_related:
                print(f"   • {table}")
        else:
            print("❌ No obvious audit/history tables found")
        
        # Check publishers table structure
        print(f"\n2️⃣ PUBLISHERS TABLE STRUCTURE:")
        print("-" * 40)
        cursor.execute("DESCRIBE publishers")
        columns = cursor.fetchall()
        
        date_columns = []
        for col in columns:
            print(f"   {col['Field']: <20} {col['Type']: <15} {col['Null']: <5} {col['Default'] or ''}")
            if any(word in col['Field'].lower() for word in ['date', 'time', 'created', 'updated', 'last']):
                date_columns.append(col['Field'])
        
        if date_columns:
            print(f"\n📅 Date/time columns found: {', '.join(date_columns)}")
        
        print(f"\n3️⃣ CURRENT ACCOUNT STATUS DISTRIBUTION:")
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
        
        print(f"\n4️⃣ INACTIVE ACCOUNTS WITH PROJECT DETAILS:")
        print("-" * 40)
        cursor.execute("""
        SELECT 
            p.syndicator_id,
            p.status,
            COUNT(gep.project_id) as total_projects,
            MIN(gep.date_created) as first_project,
            MAX(gep.date_created) as latest_project,
            DATEDIFF(NOW(), MAX(gep.date_created)) as days_since_last_project
        FROM publishers p
        JOIN geo_edge_projects gep ON p.syndicator_id = gep.syndicator_id
        WHERE p.status IN ('inactive', 'paused', 'suspended', 'frozen')
        GROUP BY p.syndicator_id, p.status
        ORDER BY latest_project DESC
        LIMIT 20
        """)
        
        inactive_details = cursor.fetchall()
        print("   Account ID    Status       Projects  Last Project    Days Ago")
        print("   " + "-" * 55)
        
        for row in inactive_details:
            print(f"   {row['syndicator_id']: <12} {row['status']: <12} {row['total_projects']: >8} "
                  f"{row['latest_project'].strftime('%Y-%m-%d'): <12} {row['days_since_last_project']: >8}")
        
        print(f"\n5️⃣ SUSPICIOUS CASES - INACTIVE WITH RECENT PROJECTS:")
        print("-" * 40)
        cursor.execute("""
        SELECT 
            p.syndicator_id,
            p.status,
            COUNT(gep.project_id) as total_projects,
            MAX(gep.date_created) as latest_project,
            DATEDIFF(NOW(), MAX(gep.date_created)) as days_since_last_project
        FROM publishers p
        JOIN geo_edge_projects gep ON p.syndicator_id = gep.syndicator_id
        WHERE p.status IN ('inactive', 'paused', 'suspended', 'frozen')
        AND gep.date_created >= DATE_SUB(NOW(), INTERVAL 7 DAYS)
        GROUP BY p.syndicator_id, p.status
        ORDER BY latest_project DESC
        """)
        
        suspicious = cursor.fetchall()
        if suspicious:
            print("🚨 ALERT: These accounts became inactive AFTER creating projects:")
            for row in suspicious:
                print(f"   🔴 Account {row['syndicator_id']} ({row['status']}): "
                      f"{row['total_projects']} projects, latest {row['days_since_last_project']} days ago")
        else:
            print("✅ No inactive accounts with recent projects (good)")
        
        print(f"\n6️⃣ PROJECT CONFIGURATION STATUS FOR INACTIVE ACCOUNTS:")
        print("-" * 40)
        cursor.execute("""
        SELECT 
            p.syndicator_id,
            p.status,
            COUNT(gep.project_id) as total_projects,
            SUM(CASE WHEN gep.auto_scan = 1 THEN 1 ELSE 0 END) as auto_scan_enabled,
            SUM(CASE WHEN gep.times_per_day > 0 THEN 1 ELSE 0 END) as has_daily_scans,
            SUM(CASE WHEN gep.auto_scan = 0 AND gep.times_per_day = 0 THEN 1 ELSE 0 END) as properly_configured
        FROM publishers p
        JOIN geo_edge_projects gep ON p.syndicator_id = gep.syndicator_id
        WHERE p.status IN ('inactive', 'paused', 'suspended', 'frozen')
        GROUP BY p.syndicator_id, p.status
        ORDER BY (total_projects - properly_configured) DESC
        """)
        
        config_status = cursor.fetchall()
        print("   Account ID    Status       Total  AutoScan  DailyScans  Correct  Needs Reset")
        print("   " + "-" * 70)
        
        total_needs_reset = 0
        for row in config_status:
            needs_reset = row['total_projects'] - row['properly_configured']
            total_needs_reset += needs_reset
            
            status_icon = "🔴" if needs_reset > 0 else "✅"
            print(f"   {status_icon} {row['syndicator_id']: <10} {row['status']: <10} "
                  f"{row['total_projects']: >5} {row['auto_scan_enabled']: >8} "
                  f"{row['has_daily_scans']: >10} {row['properly_configured']: >7} {needs_reset: >11}")
        
        print(f"\n📊 SUMMARY:")
        print(f"   • Total inactive accounts with projects: {len(config_status)}")
        print(f"   • Total projects needing reset: {total_needs_reset}")
        
        if total_needs_reset > 0:
            print(f"   🚨 ACTION REQUIRED: {total_needs_reset} projects need reset to (0,0)")
        else:
            print(f"   ✅ All inactive account projects properly configured")

if __name__ == "__main__":
    run_investigation_queries()