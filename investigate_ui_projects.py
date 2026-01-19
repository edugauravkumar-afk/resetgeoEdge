#!/usr/bin/env python3
"""
INVESTIGATE PROJECT DATES AND UPDATE STATUS
Check why these UI projects weren't updated
"""

import os
import sys
import requests
import pymysql
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv("GEOEDGE_API_KEY")
BASE_URL = "https://api.geoedge.com/rest/analytics/v3"

# Projects from UI that are showing 0/0
ui_projects = [
    ("42e140410afdf78c69e2f936704a8ee2", "46979603"),
    ("f278d092113c242a1edb5ec7ca0745d6", "46944092"),
    ("7a79aea064afb03185f440910d2351f5", "46612441"),
    ("249b3a10c104798ccc5206048de5b3c7", "46849972"),
    ("9fe55a74951aa644bea24144c7ec6347", "46926843")
]

def get_project_from_database(project_id):
    """Check if project exists in our database query"""
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
                SELECT 
                    p.project_id,
                    p.campaign_id,
                    p.locations,
                    p.creation_date,
                    sii.instruction_status
                FROM trc.geo_edge_projects AS p
                JOIN trc.sp_campaign_inventory_instructions sii ON p.campaign_id = sii.campaign_id
                WHERE p.project_id = %s
                  AND sii.instruction_status = 'ACTIVE' 
                  AND p.creation_date >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                  AND CONCAT(',', REPLACE(COALESCE(p.locations, ''), ' ', ''), ',') REGEXP ',(IT|FR|DE|ES),'
            """
            cursor.execute(sql, (project_id,))
            result = cursor.fetchone()
            return result
    finally:
        conn.close()

def update_single_project(project_id):
    """Update a single project"""
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

def main():
    print("🔍 INVESTIGATING UI PROJECTS THAT SHOW 0/0")
    print("=" * 70)
    
    projects_to_update = []
    
    for project_id, campaign_id in ui_projects:
        print(f"\n📋 PROJECT: {project_id[:12]}... (Campaign: {campaign_id})")
        
        # Check if it's in our database query
        db_result = get_project_from_database(project_id)
        
        if db_result:
            creation_date = db_result[3]
            locations = db_result[2]
            status = db_result[4]
            print(f"   ✅ Found in database")
            print(f"   📅 Created: {creation_date}")
            print(f"   🌍 Locations: {locations}")
            print(f"   📊 Status: {status}")
            projects_to_update.append(project_id)
        else:
            print(f"   ❌ NOT found in our update query")
            print(f"   🤔 Reasons could be:")
            print(f"      - Created > 7 days ago")
            print(f"      - Campaign not ACTIVE")
            print(f"      - Locations don't match IT/FR/DE/ES")
            
            # Let's check with a broader query
            print(f"   🔍 Checking with broader query...")
            # We could add more investigation here
    
    if projects_to_update:
        print(f"\n🔧 UPDATING {len(projects_to_update)} PROJECTS THAT SHOULD HAVE BEEN UPDATED")
        print("=" * 70)
        
        for i, project_id in enumerate(projects_to_update, 1):
            print(f"[{i}/{len(projects_to_update)}] Updating {project_id[:12]}...", end=" ")
            
            result = update_single_project(project_id)
            
            if result['success']:
                print(f"✅ SUCCESS")
            else:
                print(f"❌ FAILED: {result['error']}")
    else:
        print(f"\n🤔 NO PROJECTS TO UPDATE")
        print(f"All UI projects are outside our update criteria")

if __name__ == "__main__":
    main()