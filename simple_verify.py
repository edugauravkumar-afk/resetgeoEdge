#!/usr/bin/env python3
"""
Simple verification script with real-time progress
"""
import sys
import os
import requests
import pymysql
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv("GEOEDGE_API_KEY")
BASE_URL = "https://api.geoedge.com/rest/analytics/v3"

def get_projects_from_db():
    """Get all project IDs from database"""
    print("Connecting to database...", flush=True)
    
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
                SELECT DISTINCT p.project_id
                FROM trc.geo_edge_projects AS p
                JOIN trc.sp_campaign_inventory_instructions sii ON p.campaign_id = sii.campaign_id
                WHERE sii.instruction_status = 'ACTIVE' 
                  AND p.creation_date >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                  AND CONCAT(',', REPLACE(COALESCE(p.locations, ''), ' ', ''), ',') REGEXP ',(IT|FR|DE|ES),'
                ORDER BY p.creation_date DESC
            """
            cursor.execute(sql)
            rows = cursor.fetchall()
            project_ids = [row[0] for row in rows]
            print(f"Found {len(project_ids)} projects to check", flush=True)
            return project_ids
    finally:
        conn.close()

def check_project(project_id):
    """Check single project via API"""
    url = f"{BASE_URL}/projects/{project_id}"
    headers = {"Authorization": API_KEY}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if 'response' in data and 'project' in data['response']:
            project = data['response']['project']
            auto_scan = project.get('auto_scan', 0)
            times_per_day = project.get('times_per_day', 0)
            return auto_scan == 1 and times_per_day == 72
    except:
        pass
    
    return False

def main():
    print("=== PROJECT VERIFICATION STARTING ===", flush=True)
    
    # Get all projects
    project_ids = get_projects_from_db()
    total = len(project_ids)
    
    if total == 0:
        print("No projects found!", flush=True)
        return
    
    print(f"Checking {total} projects...", flush=True)
    print("=" * 50, flush=True)
    
    correct_count = 0
    incorrect_count = 0
    
    for i, project_id in enumerate(project_ids, 1):
        # Show progress every project
        print(f"[{i:4d}/{total}] Checking {project_id[:8]}... ", end="", flush=True)
        
        if check_project(project_id):
            print("✅ OK", flush=True)
            correct_count += 1
        else:
            print("❌ NEEDS UPDATE", flush=True)
            incorrect_count += 1
        
        # Summary every 50 projects
        if i % 50 == 0:
            print(f"\n--- PROGRESS UPDATE ---", flush=True)
            print(f"Checked: {i}/{total} ({i/total*100:.1f}%)", flush=True)
            print(f"Correct: {correct_count}", flush=True)
            print(f"Need Update: {incorrect_count}", flush=True)
            print("=" * 30, flush=True)
    
    # Final summary
    print("\n" + "=" * 50, flush=True)
    print("FINAL RESULTS:", flush=True)
    print(f"Total Checked: {total}", flush=True)
    print(f"✅ Correct: {correct_count}", flush=True)
    print(f"❌ Need Update: {incorrect_count}", flush=True)
    print(f"Success Rate: {correct_count/total*100:.1f}%", flush=True)
    print("=" * 50, flush=True)

if __name__ == "__main__":
    main()