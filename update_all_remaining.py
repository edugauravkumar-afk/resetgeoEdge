#!/usr/bin/env python3
"""
COMPREHENSIVE UPDATE OF ALL REMAINING PROJECTS
Find and update ALL projects that still show 0/0
"""

import os
import sys
import time
import requests
import pymysql
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv("GEOEDGE_API_KEY")
BASE_URL = "https://api.geoedge.com/rest/analytics/v3"

def get_all_projects_from_db():
    """Get ALL projects from the database (not just last 7 days)"""
    print("🔍 Connecting to database to get ALL projects...")
    
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
            # Get ALL projects targeting IT/FR/DE/ES with ACTIVE status (no date restriction)
            sql = """
                SELECT DISTINCT
                    p.project_id,
                    p.campaign_id,
                    p.locations,
                    p.creation_date
                FROM trc.geo_edge_projects AS p
                JOIN trc.sp_campaign_inventory_instructions sii ON p.campaign_id = sii.campaign_id
                WHERE sii.instruction_status = 'ACTIVE' 
                  AND CONCAT(',', REPLACE(COALESCE(p.locations, ''), ' ', ''), ',') REGEXP ',(IT|FR|DE|ES),'
                ORDER BY p.creation_date DESC
            """
            cursor.execute(sql)
            rows = cursor.fetchall()
            return [(row[0], row[1], row[2], row[3]) for row in rows]
    finally:
        conn.close()

def check_project_api_status(project_id):
    """Check project's current API status"""
    try:
        url = f"{BASE_URL}/projects/{project_id}"
        headers = {"Authorization": API_KEY}
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return {'success': False, 'error': f'HTTP {response.status_code}'}
        
        result = response.json()
        
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

def update_project_settings(project_id):
    """Update project to auto_scan=1 and times_per_day=72"""
    try:
        url = f"{BASE_URL}/projects/{project_id}"
        headers = {"Authorization": API_KEY}
        data = {
            "auto_scan": 1,
            "times_per_day": 72
        }
        
        response = requests.put(url, headers=headers, data=data, timeout=15)
        if response.status_code != 200:
            return {'success': False, 'error': f'HTTP {response.status_code}'}
        
        result = response.json()
        
        if result.get('status', {}).get('code') == 'Success':
            return {'success': True, 'message': 'Update successful'}
        else:
            return {'success': False, 'error': f'API error: {result}'}
            
    except Exception as e:
        return {'success': False, 'error': str(e)}

def verify_update(project_id):
    """Verify the update was successful"""
    time.sleep(1)  # Small delay for API processing
    
    result = check_project_api_status(project_id)
    if result['success']:
        return result['auto_scan'] == 1 and result['times_per_day'] == 72
    return False

def main():
    print("🚀 COMPREHENSIVE UPDATE OF ALL REMAINING PROJECTS")
    print("=" * 70)
    
    # Get ALL projects (no date restriction)
    all_projects = get_all_projects_from_db()
    total_projects = len(all_projects)
    print(f"✅ Found {total_projects} total ACTIVE projects targeting IT/FR/DE/ES")
    
    # Phase 1: Quick scan to find projects needing updates
    print(f"\n🔍 PHASE 1: Quick scan to identify projects needing updates...")
    print("=" * 70)
    
    projects_needing_update = []
    checked_count = 0
    
    for project_id, campaign_id, locations, created in all_projects:
        checked_count += 1
        
        # Show progress every 50 projects
        if checked_count % 50 == 0:
            print(f"[{checked_count}/{total_projects}] Scanning... Found {len(projects_needing_update)} needing updates")
        
        result = check_project_api_status(project_id)
        
        if result['success'] and result['needs_update']:
            projects_needing_update.append({
                'project_id': project_id,
                'campaign_id': campaign_id,
                'locations': locations,
                'created': created,
                'current_auto_scan': result['auto_scan'],
                'current_times_per_day': result['times_per_day']
            })
        
        time.sleep(0.05)  # Small delay to avoid rate limiting
    
    print(f"\n📊 PHASE 1 RESULTS:")
    print(f"   Total projects scanned: {total_projects}")
    print(f"   Projects needing update: {len(projects_needing_update)}")
    print(f"   Projects already correct: {total_projects - len(projects_needing_update)}")
    
    if len(projects_needing_update) == 0:
        print(f"\n🎉 ALL PROJECTS ARE ALREADY CORRECTLY CONFIGURED!")
        return 0
    
    # Phase 2: Update all projects that need it
    print(f"\n🔧 PHASE 2: Updating {len(projects_needing_update)} projects...")
    print("=" * 70)
    
    updated_count = 0
    failed_count = 0
    
    for i, project_info in enumerate(projects_needing_update, 1):
        project_id = project_info['project_id']
        campaign_id = project_info['campaign_id']
        created = project_info['created']
        
        print(f"[{i}/{len(projects_needing_update)}] {project_id[:12]}... (Campaign: {campaign_id}, Created: {created})", end=" ")
        
        # Update the project
        update_result = update_project_settings(project_id)
        
        if update_result['success']:
            # Verify the update
            if verify_update(project_id):
                updated_count += 1
                print(f"✅ SUCCESS")
            else:
                failed_count += 1
                print(f"❌ VERIFICATION FAILED")
        else:
            failed_count += 1
            print(f"❌ UPDATE FAILED: {update_result['error']}")
        
        # Show progress every 10 updates
        if i % 10 == 0:
            success_rate = (updated_count / i) * 100
            print(f"    📊 Progress: {updated_count} updated, {failed_count} failed ({success_rate:.1f}% success)")
        
        time.sleep(0.5)  # Delay between updates
    
    # Final summary
    print(f"\n" + "=" * 70)
    print(f"🏁 FINAL RESULTS:")
    print(f"   📋 Total projects needing updates: {len(projects_needing_update)}")
    print(f"   ✅ Successfully updated: {updated_count}")
    print(f"   ❌ Failed to update: {failed_count}")
    print(f"   🎯 Success rate: {(updated_count/len(projects_needing_update)*100):.1f}%")
    
    if updated_count == len(projects_needing_update):
        print(f"\n🎉 PERFECT! ALL REMAINING PROJECTS UPDATED!")
        print(f"   All projects now have auto_scan=1 and times_per_day=72")
        return 0
    else:
        print(f"\n⚠️ SOME PROJECTS STILL NEED ATTENTION")
        print(f"   {failed_count} projects failed to update")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)