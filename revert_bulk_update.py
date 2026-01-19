#!/usr/bin/env python3
"""
REVERT BULK UPDATE: Change projects from auto_scan=1, times_per_day=72 back to 0,0
Reverses the October updates that changed configuration from 0,0 to 1,72
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

def get_projects_at_1_72(days_back=90):
    """Get all projects currently set to auto_scan=1, times_per_day=72"""
    host = os.getenv("MYSQL_HOST")
    port = int(os.getenv("MYSQL_PORT", "3306"))
    user = os.getenv("MYSQL_USER")
    password = os.getenv("MYSQL_PASSWORD")
    db = os.getenv("MYSQL_DB")

    conn = pymysql.connect(
        host=host, port=port, user=user, password=password, database=db,
        charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor,
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
                WHERE p.creation_date >= DATE_SUB(NOW(), INTERVAL %s DAY)
                ORDER BY p.creation_date DESC
            """
            cursor.execute(sql, (days_back,))
            rows = cursor.fetchall()
            return rows
    finally:
        conn.close()


def get_project_config(project_id):
    """Get current project configuration from API"""
    url = f"{BASE_URL}/projects/{project_id}"
    headers = {"Authorization": API_KEY}
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        project = data.get('response', {}).get('project', {})
        return {
            'auto_scan': project.get('auto_scan'),
            'times_per_day': project.get('times_per_day'),
            'name': project.get('name')
        }
    except Exception as e:
        return None


def update_project(project_id, auto=0, times=0, dry_run=False):
    """Update single project"""
    url = f"{BASE_URL}/projects/{project_id}"
    headers = {"Authorization": API_KEY}
    data = {"auto_scan": auto, "times_per_day": times}
    
    if dry_run:
        return {"status": {"code": "DryRun", "message": f"Would revert to 0,0"}}
    
    try:
        response = requests.put(url, headers=headers, data=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        return result
    except Exception as e:
        return {"error": str(e)}


def main(dry_run=True, days_back=90):
    print("🔄 REVERTING BULK UPDATE - CHANGE 1,72 BACK TO 0,0")
    print("=" * 70)
    print(f"Mode: {'DRY RUN (Preview Only)' if dry_run else 'LIVE UPDATE'}")
    print(f"Lookback: {days_back} days")
    print("=" * 70)
    
    # Get all projects from recent period
    all_projects = get_projects_at_1_72(days_back)
    print(f"\n📊 Found {len(all_projects)} total projects in last {days_back} days")
    
    # Filter projects that are currently at 1,72
    needs_revert = []
    already_zero = []
    
    print("\n🔍 Checking current configurations...")
    for i, project in enumerate(all_projects, 1):
        project_id = project['project_id']
        
        # Get current config
        config = get_project_config(project_id)
        if not config:
            print(f"  [{i}/{len(all_projects)}] ⚠️  Could not fetch config for {project_id}")
            continue
        
        auto_scan = config.get('auto_scan')
        times_per_day = config.get('times_per_day')
        
        # Check if needs revert
        if auto_scan == 1 and times_per_day == 72:
            needs_revert.append({
                'project_id': project_id,
                'campaign_id': project.get('campaign_id'),
                'locations': project.get('locations'),
                'current_config': config
            })
        elif auto_scan == 0 and times_per_day == 0:
            already_zero.append(project_id)
    
    print(f"\n✅ Analysis Complete:")
    print(f"   • Projects at 1,72 (need revert): {len(needs_revert)}")
    print(f"   • Projects already at 0,0: {len(already_zero)}")
    
    if len(needs_revert) == 0:
        print("\n✅ No projects need reverting! All are already at 0,0 or not at 1,72")
        return 0
    
    # Show what will be reverted
    print(f"\n📋 Projects to Revert (first 10):")
    for i, item in enumerate(needs_revert[:10], 1):
        print(f"   {i}. {item['project_id']} | Campaign: {item['campaign_id']} | Locations: {item['locations']}")
    
    if len(needs_revert) > 10:
        print(f"   ... and {len(needs_revert) - 10} more")
    
    # Process reversions
    print(f"\n🔄 {'[DRY RUN] Would process' if dry_run else 'Processing'} {len(needs_revert)} projects...")
    
    success_count = 0
    failed_count = 0
    
    for i, item in enumerate(needs_revert, 1):
        project_id = item['project_id']
        progress = f"[{i}/{len(needs_revert)}]"
        
        result = update_project(project_id, auto=0, times=0, dry_run=dry_run)
        
        if 'error' in result:
            print(f"{progress} ❌ {project_id}: {result['error']}")
            failed_count += 1
        else:
            print(f"{progress} ✅ {project_id}: Reverted to 0,0")
            success_count += 1
        
        # Rate limiting
        time.sleep(0.1)
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 REVERT SUMMARY")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print(f"Projects Reverted: {success_count}")
    print(f"Projects Failed: {failed_count}")
    print(f"Projects Already at 0,0: {len(already_zero)}")
    
    if dry_run:
        print("\n⚠️  DRY RUN COMPLETE - No changes made")
        print("To apply changes, run with --live flag")
    else:
        print("\n✅ REVERT COMPLETE!")
    
    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Revert GeoEdge projects from 1,72 back to 0,0")
    parser.add_argument("--live", action="store_true", help="Apply changes (default is dry-run)")
    parser.add_argument("--days", type=int, default=90, help="Lookback window in days (default: 90)")
    
    args = parser.parse_args()
    
    dry_run = not args.live
    
    if dry_run:
        print("⚠️  Running in DRY RUN mode (no changes will be made)")
        print("Add --live flag to actually update projects\n")
    else:
        confirm = input("⚠️  WARNING: This will revert projects from 1,72 to 0,0. Continue? (yes/no): ")
        if confirm.lower() != "yes":
            print("Cancelled.")
            sys.exit(1)
    
    sys.exit(main(dry_run=dry_run, days_back=args.days))
