#!/usr/bin/env python3
"""
Update all projects for Campaign ID 46972731 to have auto_scan=1 and times_per_day=72
"""
import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key
API_KEY = os.getenv("GEOEDGE_API_KEY")
if not API_KEY:
    raise ValueError("GEOEDGE_API_KEY not found in environment variables")

BASE_URL = "https://api.geoedge.com/rest/analytics/v3"

# Project IDs for Campaign ID 46972731
PROJECT_IDS = [
    "21b98db846c7708fde86dfa2cd89c9fd",  # Already updated - verification
    "89267b98e55bab2d8a10ec59b767bb35",  # Need to update
    "e73e889e8e199d8010b9f68f587beec3"   # Need to update
]

def get_project(project_id):
    """Get project details"""
    url = f"{BASE_URL}/projects/{project_id}"
    headers = {"Authorization": API_KEY}
    
    try:
        print(f"Making GET request to: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        print(f"Response status: {response.status_code}")
        response.raise_for_status()
        data = response.json()
        print(f"Response data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
        return data
    except Exception as e:
        print(f"Error getting project {project_id}: {e}")
        print(f"Response text: {getattr(response, 'text', 'No response text')}")
        return None

def update_project(project_id, auto_scan=1, times_per_day=72, dry_run=False):
    """Update project auto_scan and times_per_day settings"""
    if dry_run:
        print(f"[DRY RUN] Would update {project_id}: auto_scan={auto_scan}, times_per_day={times_per_day}")
        return {"status": {"code": "DryRun", "message": "Dry run - no changes made"}}
    
    url = f"{BASE_URL}/projects/{project_id}"
    headers = {"Authorization": API_KEY}
    data = {
        "auto_scan": auto_scan,
        "times_per_day": times_per_day
    }
    
    try:
        response = requests.put(url, headers=headers, data=data, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error updating project {project_id}: {e}")
        return None

def main():
    print("Updating projects for Campaign ID 46972731")
    print("=" * 60)
    
    for project_id in PROJECT_IDS:
        print(f"\nProcessing project: {project_id}")
        print("-" * 40)
        
        # Get current status
        project_data = get_project(project_id)
        if project_data and 'response' in project_data and 'project' in project_data['response']:
            project = project_data['response']['project']
            current_auto_scan = project.get('auto_scan', 'N/A')
            current_times_per_day = project.get('times_per_day', 'N/A')
            project_name = project.get('name', 'Unknown')
            
            print(f"Project Name: {project_name}")
            print(f"Current: auto_scan={current_auto_scan}, times_per_day={current_times_per_day}")
            
            # Check if update needed
            if current_auto_scan == 1 and current_times_per_day == 72:
                print("✅ Already updated - no changes needed")
                continue
            
            # Update the project
            print("🔄 Updating project...")
            result = update_project(project_id, auto_scan=1, times_per_day=72)
            
            if result and result.get('status', {}).get('code') == 'Success':
                print("✅ Update successful!")
                
                # Verify the update
                updated_data = get_project(project_id)
                if updated_data and 'response' in updated_data and 'project' in updated_data['response']:
                    updated_project = updated_data['response']['project']
                    new_auto_scan = updated_project.get('auto_scan', 'N/A')
                    new_times_per_day = updated_project.get('times_per_day', 'N/A')
                    print(f"Verified: auto_scan={new_auto_scan}, times_per_day={new_times_per_day}")
                
            else:
                print(f"❌ Update failed: {result}")
        else:
            print(f"❌ Could not get project details")
    
    print("\n" + "=" * 60)
    print("Campaign ID 46972731 update process completed!")

if __name__ == "__main__":
    main()