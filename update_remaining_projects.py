#!/usr/bin/env python3
"""
UPDATE REMAINING PROJECTS
Update only the projects that need auto_scan=1 and times_per_day=72
Shows detailed progress, waits for response confirmation, double-checks each update
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

def get_projects_needing_update():
    """Get all project IDs that need updating from the database"""
    print("🔍 Connecting to database to get projects...")
    
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

def check_project_current_settings(project_id):
    """Check current project settings via API"""
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
            project_name = project.get('name', 'Unknown')
            
            return {
                'success': True,
                'auto_scan': auto_scan,
                'times_per_day': times_per_day,
                'needs_update': auto_scan != 1 or times_per_day != 72,
                'project_name': project_name
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

def verify_project_updated(project_id):
    """Double-check that the project was actually updated correctly"""
    time.sleep(1)  # Small delay for API to process
    
    result = check_project_current_settings(project_id)
    if result['success']:
        if result['auto_scan'] == 1 and result['times_per_day'] == 72:
            return {'success': True, 'verified': True}
        else:
            return {
                'success': True, 
                'verified': False,
                'auto_scan': result['auto_scan'],
                'times_per_day': result['times_per_day']
            }
    else:
        return {'success': False, 'error': result['error']}

def main():
    print("🚀 UPDATE REMAINING PROJECTS")
    print("=" * 60)
    
    # Get all projects
    print("📊 Fetching projects from database...")
    all_projects = get_projects_needing_update()
    total_projects = len(all_projects)
    print(f"✅ Found {total_projects} total projects")
    
    # First pass: identify projects that need updating
    print(f"\n🔍 PHASE 1: Identifying projects that need updating...")
    print("=" * 60)
    
    projects_to_update = []
    checked_count = 0
    
    for project_id, campaign_id, locations, created in all_projects:
        checked_count += 1
        print(f"[{checked_count}/{total_projects}] Checking {project_id[:12]}...", end=" ", flush=True)
        
        result = check_project_current_settings(project_id)
        
        if result['success']:
            if result['needs_update']:
                projects_to_update.append({
                    'project_id': project_id,
                    'campaign_id': campaign_id,
                    'locations': locations,
                    'current_auto_scan': result['auto_scan'],
                    'current_times_per_day': result['times_per_day'],
                    'project_name': result['project_name']
                })
                print(f"❌ NEEDS UPDATE (auto_scan={result['auto_scan']}, times_per_day={result['times_per_day']})")
            else:
                print(f"✅ OK")
        else:
            print(f"⚠️ ERROR: {result['error']}")
        
        # Show progress every 100 projects
        if checked_count % 100 == 0:
            print(f"\n--- Progress: {checked_count}/{total_projects} checked, {len(projects_to_update)} need updating ---")
        
        time.sleep(0.1)  # Small delay to avoid rate limiting
    
    print(f"\n📊 PHASE 1 COMPLETE:")
    print(f"   Total projects checked: {total_projects}")
    print(f"   Projects needing update: {len(projects_to_update)}")
    print(f"   Projects already correct: {total_projects - len(projects_to_update)}")
    
    if len(projects_to_update) == 0:
        print(f"\n🎉 ALL PROJECTS ARE ALREADY CORRECTLY CONFIGURED!")
        print(f"   No updates needed. All {total_projects} projects have auto_scan=1 and times_per_day=72")
        return 0
    
    # Second pass: update projects that need it
    print(f"\n🔧 PHASE 2: Updating {len(projects_to_update)} projects...")
    print("=" * 60)
    
    updated_count = 0
    failed_count = 0
    verification_failed = 0
    
    for i, project_info in enumerate(projects_to_update, 1):
        project_id = project_info['project_id']
        project_name = project_info['project_name']
        current_auto_scan = project_info['current_auto_scan']
        current_times_per_day = project_info['current_times_per_day']
        
        print(f"\n[{i}/{len(projects_to_update)}] UPDATING PROJECT: {project_id[:12]}")
        print(f"   Name: {project_name}")
        print(f"   Campaign: {project_info['campaign_id']}")
        print(f"   Current: auto_scan={current_auto_scan}, times_per_day={current_times_per_day}")
        print(f"   Target:  auto_scan=1, times_per_day=72")
        
        # Perform the update
        print(f"   🔄 Sending update request...", end=" ", flush=True)
        update_result = update_project_settings(project_id)
        
        if update_result['success']:
            print(f"✅ UPDATE SENT")
            
            # Wait and verify the update
            print(f"   ⏳ Waiting 2 seconds for API to process...", end=" ", flush=True)
            time.sleep(2)
            print(f"Done")
            
            print(f"   🔍 Verifying update...", end=" ", flush=True)
            verify_result = verify_project_updated(project_id)
            
            if verify_result['success'] and verify_result['verified']:
                updated_count += 1
                print(f"✅ VERIFIED CORRECT")
                print(f"   🎯 Project successfully updated and verified!")
            else:
                verification_failed += 1
                if verify_result['success']:
                    print(f"❌ VERIFICATION FAILED")
                    print(f"   ⚠️ Update sent but verification shows: auto_scan={verify_result['auto_scan']}, times_per_day={verify_result['times_per_day']}")
                else:
                    print(f"❌ VERIFICATION ERROR: {verify_result['error']}")
        else:
            failed_count += 1
            print(f"❌ UPDATE FAILED: {update_result['error']}")
        
        # Show progress
        print(f"   📊 Progress: {updated_count} updated, {failed_count} failed, {verification_failed} verification issues")
        
        # Small delay between projects
        time.sleep(1)
    
    # Final summary
    print(f"\n" + "=" * 60)
    print(f"🏁 FINAL RESULTS:")
    print(f"   📋 Projects that needed updating: {len(projects_to_update)}")
    print(f"   ✅ Successfully updated and verified: {updated_count}")
    print(f"   ❌ Failed to update: {failed_count}")
    print(f"   ⚠️ Updated but verification failed: {verification_failed}")
    print(f"   🎯 Success rate: {(updated_count/len(projects_to_update)*100):.1f}%")
    
    if updated_count == len(projects_to_update):
        print(f"\n🎉 PERFECT! ALL PROJECTS SUCCESSFULLY UPDATED!")
        print(f"   All {len(projects_to_update)} projects now have auto_scan=1 and times_per_day=72")
        return 0
    elif updated_count > 0:
        print(f"\n✅ GOOD PROGRESS!")
        print(f"   {updated_count} projects successfully updated")
        if failed_count + verification_failed > 0:
            print(f"   {failed_count + verification_failed} projects still need attention")
        return 1
    else:
        print(f"\n❌ NO PROJECTS WERE SUCCESSFULLY UPDATED")
        print(f"   All {len(projects_to_update)} projects still need updating")
        return 2

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)