#!/usr/bin/env python3
"""
START BULK UPDATE: Update all projects to auto_scan=1, times_per_day=72
"""
import sys
import os
sys.path.append('/Users/gaurav.k/Desktop/geoedge-country-projects')

import requests
import time
import pymysql
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv("GEOEDGE_API_KEY")
BASE_URL = "https://api.geoedge.com/rest/analytics/v3"

# Already updated projects (Campaign ID 46972731)
ALREADY_UPDATED = [
    "21b98db846c7708fde86dfa2cd89c9fd",
    "89267b98e55bab2d8a10ec59b767bb35", 
    "e73e889e8e199d8010b9f68f587beec3"
]

def get_all_projects():
    """Get all projects from database"""
    host = os.getenv("MYSQL_HOST")
    port = int(os.getenv("MYSQL_PORT", "3306"))
    user = os.getenv("MYSQL_USER")
    password = os.getenv("MYSQL_PASSWORD")
    db = os.getenv("MYSQL_DB")

    conn = pymysql.connect(
        host=host, port=port, user=user, password=password, database=db,
        charset="utf8mb4", cursorclass=pymysql.cursors.Cursor,
        autocommit=True, read_timeout=60, write_timeout=60,
    )

    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT DISTINCT
                    p.project_id,
                    p.campaign_id
                FROM trc.geo_edge_projects AS p
                JOIN trc.sp_campaign_inventory_instructions sii ON p.campaign_id = sii.campaign_id
                WHERE sii.instruction_status = 'ACTIVE' 
                  AND p.creation_date >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                  AND CONCAT(',', REPLACE(COALESCE(p.locations, ''), ' ', ''), ',') REGEXP ',(IT|FR|DE|ES),'
                ORDER BY p.creation_date DESC
            """
            cursor.execute(sql)
            rows = cursor.fetchall()
            return [row[0] for row in rows if row[0] not in ALREADY_UPDATED]
    finally:
        conn.close()

def update_project(project_id):
    """Update single project"""
    url = f"{BASE_URL}/projects/{project_id}"
    headers = {"Authorization": API_KEY}
    data = {"auto_scan": 1, "times_per_day": 72}
    
    try:
        response = requests.put(url, headers=headers, data=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        return result.get('status', {}).get('code') == 'Success'
    except Exception as e:
        print(f"❌ Error updating {project_id}: {e}")
        return False

def main():
    print("🚀 STARTING BULK UPDATE FOR ALL PROJECTS")
    print("Target: auto_scan=1, times_per_day=72")
    print("=" * 60)
    
    # Get all project IDs
    project_ids = get_all_projects()
    total = len(project_ids)
    
    print(f"📊 Found {total} projects to update")
    print(f"⏭️  Excluding {len(ALREADY_UPDATED)} already updated")
    print("=" * 60)
    
    if total == 0:
        print("✅ No projects need updating!")
        return
    
    # Process projects
    success_count = 0
    failed_count = 0
    
    for i, project_id in enumerate(project_ids, 1):
        progress = f"[{i}/{total}]"
        print(f"{progress} Processing {project_id}...")
        
        if update_project(project_id):
            success_count += 1
            print(f"{progress} ✅ SUCCESS - {project_id}")
        else:
            failed_count += 1
            print(f"{progress} ❌ FAILED - {project_id}")
        
        # Progress update every 50 projects
        if i % 50 == 0:
            print(f"\n📈 PROGRESS UPDATE:")
            print(f"   Processed: {i}/{total}")
            print(f"   Success: {success_count}")
            print(f"   Failed: {failed_count}")
            print(f"   Success Rate: {success_count/i*100:.1f}%")
            print("=" * 40)
        
        # Small delay between requests
        time.sleep(0.5)
    
    # Final summary
    print(f"\n🎯 FINAL RESULTS:")
    print(f"   Total Processed: {total}")
    print(f"   ✅ Successful: {success_count}")
    print(f"   ❌ Failed: {failed_count}")
    print(f"   📊 Success Rate: {success_count/total*100:.1f}%")
    print("=" * 60)
    
    if success_count == total:
        print("🎉 ALL PROJECTS UPDATED SUCCESSFULLY!")
    else:
        print(f"⚠️  {failed_count} projects failed to update")

if __name__ == "__main__":
    main()