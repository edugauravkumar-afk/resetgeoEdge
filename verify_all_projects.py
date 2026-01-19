#!/usr/bin/env python3
"""
COMPREHENSIVE PROJECT VERIFICATION
Checks ALL projects to see which ones still need auto_scan=1 and times_per_day=72
Shows live progress and creates list of projects that need updating
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

def get_all_projects():
    """Get all projects from database that match our criteria"""
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
            cursor.execute(sql)
            rows = cursor.fetchall()
            return [(row[0], row[1], row[2], row[3]) for row in rows]
    finally:
        conn.close()

def check_project_api(project_id):
    """Check single project via API"""
    url = f"{BASE_URL}/projects/{project_id}"
    headers = {"Authorization": API_KEY}
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        # Handle API response structure
        if 'response' in result and 'project' in result['response']:
            project = result['response']['project']
            auto_scan = project.get('auto_scan', 0)
            times_per_day = project.get('times_per_day', 0)
            name = project.get('name', 'Unknown')
            return {
                'success': True,
                'auto_scan': auto_scan,
                'times_per_day': times_per_day,
                'name': name,
                'needs_update': auto_scan != 1 or times_per_day != 72
            }
        else:
            return {'success': False, 'error': 'Invalid API response structure'}
            
    except Exception as e:
        return {'success': False, 'error': str(e)}

def main():
    print("🔍 COMPREHENSIVE PROJECT VERIFICATION")
    print("Checking ALL projects for auto_scan=1 and times_per_day=72")
    print("=" * 70)
    
    # Get all project IDs from database
    print("📊 Fetching projects from database...")
    projects = get_all_projects()
    total = len(projects)
    
    print(f"Found {total} total projects matching criteria")
    print("=" * 70)
    
    if total == 0:
        print("✅ No projects found!")
        return
    
    # Track results
    checked_count = 0
    success_count = 0
    failed_checks = 0
    needs_update = []
    already_correct = []
    api_errors = []
    
    print("🚀 Starting verification...")
    print("Format: [Progress] Project_ID -> Status")
    print("-" * 70)
    
    # Check each project via API
    for i, (project_id, campaign_id, locations, created) in enumerate(projects, 1):
        progress = f"[{i}/{total}]"
        
        print(f"{progress} Checking {project_id}...", end=" ")
        sys.stdout.flush()
        
        result = check_project_api(project_id)
        checked_count += 1
        
        if result['success']:
            auto_scan = result['auto_scan']
            times_per_day = result['times_per_day']
            name = result['name']
            
            if result['needs_update']:
                needs_update.append({
                    'project_id': project_id,
                    'campaign_id': campaign_id,
                    'auto_scan': auto_scan,
                    'times_per_day': times_per_day,
                    'name': name
                })
                print(f"❌ NEEDS UPDATE (auto_scan={auto_scan}, times_per_day={times_per_day})")
            else:
                already_correct.append(project_id)
                print(f"✅ CORRECT (auto_scan={auto_scan}, times_per_day={times_per_day})")
            
            success_count += 1
        else:
            api_errors.append({
                'project_id': project_id,
                'error': result['error']
            })
            failed_checks += 1
            print(f"⚠️ API ERROR: {result['error']}")
        
        # Progress summary every 25 projects
        if i % 25 == 0:
            print(f"\n📈 PROGRESS UPDATE [{i}/{total}]:")
            print(f"   ✅ Correctly configured: {len(already_correct)}")
            print(f"   ❌ Need updating: {len(needs_update)}")
            print(f"   ⚠️ API errors: {len(api_errors)}")
            print(f"   📊 Success rate: {success_count/checked_count*100:.1f}%")
            print("-" * 50)
        
        # Small delay to avoid overwhelming API
        time.sleep(0.2)
    
    # Final comprehensive report
    print(f"\n🎯 FINAL VERIFICATION RESULTS:")
    print("=" * 70)
    print(f"📊 Total projects checked: {total}")
    print(f"✅ Already correct: {len(already_correct)}")
    print(f"❌ Need updating: {len(needs_update)}")
    print(f"⚠️ API errors: {len(api_errors)}")
    print(f"📈 API success rate: {success_count/checked_count*100:.1f}%")
    
    # Save projects that need updating to file
    if needs_update:
        print(f"\n📝 PROJECTS NEEDING UPDATE ({len(needs_update)}):")
        print("-" * 50)
        
        with open('projects_needing_update.txt', 'w') as f:
            f.write(f"# Projects needing update - Generated {datetime.now()}\n")
            f.write(f"# Total: {len(needs_update)} projects\n")
            f.write("# Format: project_id,campaign_id,current_auto_scan,current_times_per_day,name\n\n")
            
            for i, proj in enumerate(needs_update, 1):
                project_line = f"{proj['project_id']},{proj['campaign_id']},{proj['auto_scan']},{proj['times_per_day']},{proj['name']}"
                f.write(project_line + "\n")
                
                # Print first 10 for immediate visibility
                if i <= 10:
                    print(f"  {i:2d}. {proj['project_id']} (Campaign: {proj['campaign_id']}) -> auto_scan={proj['auto_scan']}, times_per_day={proj['times_per_day']}")
            
            if len(needs_update) > 10:
                print(f"     ... and {len(needs_update) - 10} more (see projects_needing_update.txt)")
        
        print(f"\n💾 Full list saved to: projects_needing_update.txt")
        
    else:
        print(f"\n🎉 ALL PROJECTS ARE CORRECTLY CONFIGURED!")
    
    # Save API errors if any
    if api_errors:
        print(f"\n⚠️ API ERRORS ({len(api_errors)}):")
        with open('api_errors.txt', 'w') as f:
            f.write(f"# API errors - Generated {datetime.now()}\n\n")
            for error in api_errors:
                f.write(f"{error['project_id']}: {error['error']}\n")
                print(f"  {error['project_id']}: {error['error']}")
        print(f"💾 API errors saved to: api_errors.txt")
    
    print("=" * 70)
    
    if needs_update:
        print(f"🔧 NEXT STEP: Run update script for {len(needs_update)} projects")
        return 1  # Exit code 1 indicates projects need updating
    else:
        print(f"✅ VERIFICATION COMPLETE: All projects correctly configured!")
        return 0  # Exit code 0 indicates success

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)