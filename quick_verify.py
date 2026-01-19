#!/usr/bin/env python3
"""
QUICK PROJECT VERIFICATION
Fast check to see which projects still need updating
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

def get_recent_projects():
    """Get projects from database"""
    print("📊 Connecting to database...")
    
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
                    p.campaign_id,
                    p.locations,
                    p.creation_date
                FROM trc.geo_edge_projects AS p
                JOIN trc.sp_campaign_inventory_instructions sii ON p.campaign_id = sii.campaign_id
                WHERE sii.instruction_status = 'ACTIVE' 
                  AND p.creation_date >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                  AND CONCAT(',', REPLACE(COALESCE(p.locations, ''), ' ', ''), ',') REGEXP ',(IT|FR|DE|ES),'
                ORDER BY p.creation_date DESC
            """
            print("🔍 Executing database query...")
            cursor.execute(sql)
            rows = cursor.fetchall()
            print(f"✅ Found {len(rows)} projects from database")
            return [(row[0], row[1], row[2], row[3]) for row in rows]
    finally:
        conn.close()

def check_project_quick(project_id):
    """Quick API check for a single project"""
    url = f"{BASE_URL}/projects/{project_id}"
    headers = {"Authorization": API_KEY}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return {'success': False, 'error': f'HTTP {response.status_code}'}
        
        result = response.json()
        
        # Handle API response structure
        if 'response' in result and 'project' in result['response']:
            project = result['response']['project']
            auto_scan = project.get('auto_scan', 0)
            times_per_day = project.get('times_per_day', 0)
            
            return {
                'success': True,
                'auto_scan': auto_scan,
                'times_per_day': times_per_day,
                'needs_update': auto_scan != 1 or times_per_day != 72
            }
        else:
            return {'success': False, 'error': 'Invalid response structure'}
            
    except Exception as e:
        return {'success': False, 'error': str(e)}

def main():
    print("🚀 QUICK PROJECT VERIFICATION")
    print("=" * 50)
    
    # Get projects
    projects = get_recent_projects()
    total = len(projects)
    
    if total == 0:
        print("❌ No projects found!")
        return
    
    print(f"\n🔍 Checking {total} projects via API...")
    print("=" * 50)
    
    # Take sample of first 10 projects for quick check
    sample_projects = projects[:10]
    print(f"📋 Quick sample check of first {len(sample_projects)} projects:")
    
    needs_update = []
    correct = []
    errors = []
    
    for i, (project_id, campaign_id, locations, created) in enumerate(sample_projects, 1):
        print(f"  [{i}/10] {project_id}...", end=" ", flush=True)
        
        result = check_project_quick(project_id)
        
        if result['success']:
            if result['needs_update']:
                needs_update.append(project_id)
                print(f"❌ NEEDS UPDATE (auto_scan={result['auto_scan']}, times_per_day={result['times_per_day']})")
            else:
                correct.append(project_id)
                print(f"✅ OK (auto_scan={result['auto_scan']}, times_per_day={result['times_per_day']})")
        else:
            errors.append(project_id)
            print(f"⚠️ ERROR: {result['error']}")
        
        time.sleep(0.1)  # Small delay
    
    # Summary
    print(f"\n📊 SAMPLE RESULTS:")
    print(f"   ✅ Correct: {len(correct)}")
    print(f"   ❌ Need update: {len(needs_update)}")
    print(f"   ⚠️ Errors: {len(errors)}")
    
    if needs_update:
        print(f"\n❌ ISSUES FOUND! Projects needing update:")
        for pid in needs_update:
            print(f"     {pid}")
        
        print(f"\n🔧 RECOMMENDATION:")
        print(f"   - {len(needs_update)}/{len(sample_projects)} sample projects need updating")
        print(f"   - Estimated {len(needs_update)/len(sample_projects)*total:.0f} total projects may need updating")
        print(f"   - Run full bulk update to fix all {total} projects")
        
        # Ask user if they want to run update
        print(f"\n🤔 Would you like to run the bulk update script? (Creates update_remaining.py)")
        return 1
    else:
        print(f"\n🎉 SAMPLE LOOKS GOOD!")
        print(f"   All {len(sample_projects)} sample projects are correctly configured")
        print(f"   Likely all {total} projects are also correct")
        return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)