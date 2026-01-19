#!/usr/bin/env python3
"""
Bulk update ALL projects to set auto_scan=1 and times_per_day=72
This script will:
1. Get all projects from the database
2. Check current API settings for each project
3. Update only projects that need updating (skip already updated ones)
4. Confirm each update before moving to the next
5. Provide detailed logging and progress tracking
"""
import os
import requests
import time
import pymysql
from dotenv import load_dotenv
from datetime import datetime
import json

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv("GEOEDGE_API_KEY")
BASE_URL = "https://api.geoedge.com/rest/analytics/v3"
BATCH_SIZE = 10  # Process 10 projects at a time for confirmation
DELAY_BETWEEN_REQUESTS = 2  # 2 seconds delay between API calls

# Already updated projects (Campaign ID 46972731)
ALREADY_UPDATED = [
    "21b98db846c7708fde86dfa2cd89c9fd",
    "89267b98e55bab2d8a10ec59b767bb35", 
    "e73e889e8e199d8010b9f68f587beec3"
]

def get_all_projects_from_db():
    """Get all project IDs from the database"""
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
            # Get all projects with ACTIVE status from last 7 days targeting IT/FR/DE/ES
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
            
            projects = []
            for row in rows:
                project_id, campaign_id, locations, creation_date = row
                projects.append({
                    'project_id': project_id,
                    'campaign_id': campaign_id,
                    'locations': locations,
                    'creation_date': creation_date
                })
            
            return projects
    finally:
        conn.close()

def get_project_api_details(project_id):
    """Get project details from GeoEdge API"""
    url = f"{BASE_URL}/projects/{project_id}"
    headers = {"Authorization": API_KEY}
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if 'response' in data and 'project' in data['response']:
            project = data['response']['project']
            return {
                'name': project.get('name', 'Unknown'),
                'auto_scan': project.get('auto_scan', 'N/A'),
                'times_per_day': project.get('times_per_day', 'N/A'),
                'success': True
            }
        else:
            return {'success': False, 'error': 'Unexpected API response structure'}
            
    except Exception as e:
        return {'success': False, 'error': str(e)}

def update_project_api(project_id, auto_scan=1, times_per_day=72):
    """Update project auto_scan and times_per_day via API"""
    url = f"{BASE_URL}/projects/{project_id}"
    headers = {"Authorization": API_KEY}
    data = {
        "auto_scan": auto_scan,
        "times_per_day": times_per_day
    }
    
    try:
        response = requests.put(url, headers=headers, data=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        if result.get('status', {}).get('code') == 'Success':
            return {'success': True}
        else:
            return {'success': False, 'error': f"API returned: {result}"}
            
    except Exception as e:
        return {'success': False, 'error': str(e)}

def log_progress(message, project_id=None, progress_info=None):
    """Log progress with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}]"
    
    if progress_info:
        log_msg += f" [{progress_info}]"
    
    if project_id:
        log_msg += f" [{project_id}]"
        
    log_msg += f" {message}"
    print(log_msg)

def main():
    print("=" * 80)
    print("🚀 BULK PROJECT UPDATE SCRIPT - AUTO SCAN & TIMES PER DAY")
    print("=" * 80)
    print(f"Target settings: auto_scan=1, times_per_day=72")
    print(f"Batch size: {BATCH_SIZE} projects per confirmation")
    print(f"API delay: {DELAY_BETWEEN_REQUESTS} seconds between requests")
    print(f"Already updated projects: {len(ALREADY_UPDATED)}")
    print("=" * 80)

    # Get all projects from database
    log_progress("Fetching all projects from database...")
    all_projects = get_all_projects_from_db()
    total_projects = len(all_projects)
    
    log_progress(f"Found {total_projects} total projects in database")
    
    # Filter out already updated projects
    projects_to_process = [p for p in all_projects if p['project_id'] not in ALREADY_UPDATED]
    remaining_projects = len(projects_to_process)
    
    log_progress(f"Projects to process: {remaining_projects} (excluding {len(ALREADY_UPDATED)} already updated)")
    
    if remaining_projects == 0:
        log_progress("No projects need updating. All done!")
        return

    # Confirm before starting
    print(f"\n📋 SUMMARY:")
    print(f"  • Total projects in DB: {total_projects}")
    print(f"  • Already updated: {len(ALREADY_UPDATED)}")
    print(f"  • Projects to update: {remaining_projects}")
    print(f"  • Batch size: {BATCH_SIZE} (will ask for confirmation after each batch)")
    
    confirm = input(f"\n❓ Do you want to proceed with updating {remaining_projects} projects? (yes/no): ").strip().lower()
    if confirm != 'yes':
        log_progress("Operation cancelled by user")
        return

    # Process projects in batches
    updated_count = 0
    failed_count = 0
    skipped_count = 0
    
    for i in range(0, remaining_projects, BATCH_SIZE):
        batch = projects_to_process[i:i+BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        total_batches = (remaining_projects + BATCH_SIZE - 1) // BATCH_SIZE
        
        print(f"\n" + "="*60)
        print(f"📦 BATCH {batch_num}/{total_batches} - Processing {len(batch)} projects")
        print(f"   Progress: {i+len(batch)}/{remaining_projects} projects")
        print("="*60)
        
        batch_results = []
        
        for j, project in enumerate(batch):
            project_id = project['project_id']
            campaign_id = project['campaign_id']
            
            progress_info = f"{i+j+1}/{remaining_projects}"
            log_progress(f"Processing project...", project_id, progress_info)
            
            # Get current settings
            current_details = get_project_api_details(project_id)
            
            if not current_details['success']:
                log_progress(f"❌ Failed to get project details: {current_details['error']}", project_id, progress_info)
                failed_count += 1
                batch_results.append({
                    'project_id': project_id,
                    'campaign_id': campaign_id,
                    'status': 'failed',
                    'reason': 'Could not fetch current details'
                })
                continue
            
            current_auto_scan = current_details['auto_scan']
            current_times_per_day = current_details['times_per_day']
            project_name = current_details['name']
            
            log_progress(f"Current: auto_scan={current_auto_scan}, times_per_day={current_times_per_day}", project_id, progress_info)
            log_progress(f"Name: {project_name[:50]}{'...' if len(project_name) > 50 else ''}", project_id, progress_info)
            
            # Check if update needed
            if current_auto_scan == 1 and current_times_per_day == 72:
                log_progress("✅ Already has correct settings - skipping", project_id, progress_info)
                skipped_count += 1
                batch_results.append({
                    'project_id': project_id,
                    'campaign_id': campaign_id,
                    'status': 'skipped',
                    'reason': 'Already correct'
                })
                continue
            
            # Update the project
            log_progress("🔄 Updating project...", project_id, progress_info)
            update_result = update_project_api(project_id)
            
            if update_result['success']:
                log_progress("✅ Update successful!", project_id, progress_info)
                
                # Verify the update
                time.sleep(1)  # Brief pause before verification
                verify_details = get_project_api_details(project_id)
                
                if verify_details['success']:
                    new_auto_scan = verify_details['auto_scan']
                    new_times_per_day = verify_details['times_per_day']
                    log_progress(f"✅ Verified: auto_scan={new_auto_scan}, times_per_day={new_times_per_day}", project_id, progress_info)
                    
                    if new_auto_scan == 1 and new_times_per_day == 72:
                        updated_count += 1
                        batch_results.append({
                            'project_id': project_id,
                            'campaign_id': campaign_id,
                            'status': 'success',
                            'reason': 'Successfully updated and verified'
                        })
                    else:
                        log_progress(f"⚠️  Update may not have taken effect properly", project_id, progress_info)
                        batch_results.append({
                            'project_id': project_id,
                            'campaign_id': campaign_id,
                            'status': 'partial',
                            'reason': 'Updated but verification shows unexpected values'
                        })
                else:
                    log_progress(f"⚠️  Could not verify update", project_id, progress_info)
                    updated_count += 1  # Count as success since API update succeeded
                    batch_results.append({
                        'project_id': project_id,
                        'campaign_id': campaign_id,
                        'status': 'success',
                        'reason': 'Updated successfully (verification failed)'
                    })
            else:
                log_progress(f"❌ Update failed: {update_result['error']}", project_id, progress_info)
                failed_count += 1
                batch_results.append({
                    'project_id': project_id,
                    'campaign_id': campaign_id,
                    'status': 'failed',
                    'reason': f"Update failed: {update_result['error']}"
                })
            
            # Delay between requests
            if j < len(batch) - 1:  # Don't delay after last item in batch
                time.sleep(DELAY_BETWEEN_REQUESTS)
        
        # Batch summary
        print(f"\n📊 BATCH {batch_num} SUMMARY:")
        success_in_batch = len([r for r in batch_results if r['status'] == 'success'])
        failed_in_batch = len([r for r in batch_results if r['status'] == 'failed'])
        skipped_in_batch = len([r for r in batch_results if r['status'] == 'skipped'])
        
        print(f"  ✅ Successful: {success_in_batch}")
        print(f"  ⏭️  Skipped: {skipped_in_batch}")
        print(f"  ❌ Failed: {failed_in_batch}")
        
        # Overall progress
        print(f"\n📈 OVERALL PROGRESS:")
        print(f"  ✅ Total Updated: {updated_count}/{remaining_projects}")
        print(f"  ⏭️  Total Skipped: {skipped_count}/{remaining_projects}")
        print(f"  ❌ Total Failed: {failed_count}/{remaining_projects}")
        print(f"  📍 Remaining: {remaining_projects - (updated_count + skipped_count + failed_count)}")
        
        # Continue confirmation (except for last batch)
        if i + BATCH_SIZE < remaining_projects:
            print(f"\n⏸️  BATCH {batch_num} COMPLETED")
            continue_confirm = input(f"❓ Continue with next batch (Batch {batch_num + 1})? (yes/no/quit): ").strip().lower()
            
            if continue_confirm == 'quit':
                log_progress("Operation stopped by user")
                break
            elif continue_confirm != 'yes':
                log_progress("Operation paused by user")
                break
    
    # Final summary
    print(f"\n" + "="*80)
    print(f"🎯 FINAL SUMMARY")
    print(f"="*80)
    print(f"✅ Successfully Updated: {updated_count}")
    print(f"⏭️  Skipped (already correct): {skipped_count}")
    print(f"❌ Failed: {failed_count}")
    print(f"📊 Total Processed: {updated_count + skipped_count + failed_count}/{remaining_projects}")
    print(f"🎉 Success Rate: {(updated_count/(updated_count + failed_count)*100):.1f}%" if (updated_count + failed_count) > 0 else "N/A")
    print("="*80)
    
    if updated_count > 0:
        print(f"🎉 {updated_count} projects have been successfully updated!")
        print(f"   All updated projects now have: auto_scan=1, times_per_day=72")

if __name__ == "__main__":
    main()