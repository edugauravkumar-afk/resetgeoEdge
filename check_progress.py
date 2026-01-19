#!/usr/bin/env python3

import os
import sys
import time
from dotenv import load_dotenv
import pymysql
import requests

# Load environment variables
load_dotenv()

def get_db_connection():
    return pymysql.connect(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME'),
        charset='utf8mb4'
    )

def get_projects():
    """Get all projects targeting IT/FR/DE/ES from last 7 days"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            query = """
            SELECT DISTINCT p.project_id, p.campaign_id
            FROM sp_campaign_inventory_instructions p
            JOIN sp_campaign_inventory_instructions_geos g ON p.id = g.instruction_id
            WHERE p.created >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            AND g.geo_code REGEXP '^(IT|FR|DE|ES)$'
            ORDER BY p.created DESC
            """
            cursor.execute(query)
            return cursor.fetchall()
    finally:
        conn.close()

def check_project_settings(project_id):
    """Check a single project's settings via API"""
    try:
        url = f"https://admin.geoedge.be/api/project/{project_id}"
        headers = {
            'Authorization': f"Bearer {os.getenv('GEOEDGE_API_TOKEN')}"
        }
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            project_data = data.get('response', {}).get('project', {})
            auto_scan = project_data.get('auto_scan', 0)
            times_per_day = project_data.get('times_per_day', 0)
            return auto_scan, times_per_day
        else:
            return None, None
    except Exception as e:
        return None, None

def main():
    print("🔍 Fetching projects from database...")
    projects = get_projects()
    total_projects = len(projects)
    
    print(f"📊 Found {total_projects} projects to check")
    print("=" * 60)
    
    correct_count = 0
    incorrect_count = 0
    failed_count = 0
    incorrect_projects = []
    
    for i, (project_id, campaign_id) in enumerate(projects, 1):
        # Show progress
        print(f"\r🔍 Checking project {i}/{total_projects} ({project_id[:12]}...)", end='', flush=True)
        
        auto_scan, times_per_day = check_project_settings(project_id)
        
        if auto_scan is None:
            failed_count += 1
        elif auto_scan == 1 and times_per_day == 72:
            correct_count += 1
        else:
            incorrect_count += 1
            incorrect_projects.append({
                'project_id': project_id,
                'campaign_id': campaign_id,
                'auto_scan': auto_scan,
                'times_per_day': times_per_day
            })
        
        # Show running totals every 10 projects
        if i % 10 == 0:
            print(f"\n📈 Progress: ✅ {correct_count} correct | ❌ {incorrect_count} incorrect | 🚫 {failed_count} failed")
        
        # Small delay to avoid rate limiting
        time.sleep(0.1)
    
    print(f"\n")
    print("=" * 60)
    print("📋 FINAL RESULTS:")
    print(f"✅ Correctly configured: {correct_count}")
    print(f"❌ Incorrectly configured: {incorrect_count}")
    print(f"🚫 Failed to check: {failed_count}")
    print(f"📊 Total checked: {total_projects}")
    
    if incorrect_projects:
        print(f"\n🔧 Projects needing updates:")
        for proj in incorrect_projects[:10]:  # Show first 10
            print(f"  - {proj['project_id'][:12]}... (Campaign: {proj['campaign_id']}) - auto_scan: {proj['auto_scan']}, times_per_day: {proj['times_per_day']}")
        
        if len(incorrect_projects) > 10:
            print(f"  ... and {len(incorrect_projects) - 10} more")
        
        # Save to file for bulk update
        with open('projects_to_update.txt', 'w') as f:
            for proj in incorrect_projects:
                f.write(f"{proj['project_id']}\n")
        print(f"\n💾 Saved {len(incorrect_projects)} project IDs to 'projects_to_update.txt'")

if __name__ == "__main__":
    main()