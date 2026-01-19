#!/usr/bin/env python3
"""
Fix the visible UI projects that weren't updated properly
"""
import os
import requests
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv("GEOEDGE_API_KEY")
BASE_URL = "https://api.geoedge.com/rest/analytics/v3"

# Projects from the UI that should be updated but aren't
ui_projects_to_fix = [
    "9977af226d2a4840d5f48a8900843bc8",
    "d92241d5e062e943f1627e0cabcf4646", 
    "48898b86f28b62fe918bb1ef4db12850",
    "48a6ca7e128205f5fcf1e51c49fa70d8",
    "5a68192c88472f878ada8951d8b6bbca"
]

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

def verify_project(project_id):
    """Verify project settings"""
    url = f"{BASE_URL}/projects/{project_id}"
    headers = {"Authorization": API_KEY}
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if 'response' in data and 'project' in data['response']:
            project = data['response']['project']
            auto_scan = project.get('auto_scan', 'N/A')
            times_per_day = project.get('times_per_day', 'N/A')
            return auto_scan, times_per_day
        return None, None
    except Exception as e:
        print(f"❌ Error verifying {project_id}: {e}")
        return None, None

def main():
    print("🔧 FIXING UI PROJECTS THAT WEREN'T UPDATED")
    print("=" * 60)
    
    success_count = 0
    failed_count = 0
    
    for i, project_id in enumerate(ui_projects_to_fix, 1):
        print(f"[{i}/{len(ui_projects_to_fix)}] Processing {project_id}...")
        
        # Check current state
        auto_scan, times_per_day = verify_project(project_id)
        print(f"  Current: auto_scan={auto_scan}, times_per_day={times_per_day}")
        
        if auto_scan == 1 and times_per_day == 72:
            print(f"  ✅ Already correct - skipping")
            success_count += 1
            continue
        
        # Update the project
        print(f"  🔄 Updating...")
        if update_project(project_id):
            # Verify the update
            time.sleep(1)
            new_auto_scan, new_times_per_day = verify_project(project_id)
            
            if new_auto_scan == 1 and new_times_per_day == 72:
                print(f"  ✅ SUCCESS - Updated to auto_scan={new_auto_scan}, times_per_day={new_times_per_day}")
                success_count += 1
            else:
                print(f"  ⚠️  Update may not have taken effect: auto_scan={new_auto_scan}, times_per_day={new_times_per_day}")
                failed_count += 1
        else:
            print(f"  ❌ FAILED to update")
            failed_count += 1
        
        print()
        time.sleep(1)  # Brief delay between updates
    
    print("=" * 60)
    print(f"🎯 RESULTS:")
    print(f"  ✅ Successful: {success_count}")
    print(f"  ❌ Failed: {failed_count}")
    print(f"  📊 Success Rate: {success_count/(success_count+failed_count)*100:.1f}%")
    
    if success_count == len(ui_projects_to_fix):
        print("\n🎉 All UI projects now have correct settings!")
        print("Please refresh the Streamlit dashboard to see the changes.")
    else:
        print(f"\n⚠️  {failed_count} projects still need attention.")

if __name__ == "__main__":
    main()