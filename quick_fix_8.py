#!/usr/bin/env python3
"""
QUICK UPDATE FOR NEW UI PROJECTS
Update the 8 new projects from the user's list showing 0/0
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

# Just the 8 new projects from user's list
new_projects_to_fix = [
    "6196a9342532dff7f78dab576414ce8a",  # Campaign 46943736, DE
    "4c366ca963ca77ab05132c461621b651",  # Campaign 47000620, DE
    "abf711007bdc0deff8e97314709014e5",  # Campaign 46951962, DE
    "1d850c67696722a63203befc5dfab77a",  # Campaign 46943036, DE
    "ce331161cab4bb0af318508399d45fbc",  # Campaign 47004327, DE
    "817ceade7ede1943bef541286245c3c2",  # Campaign 46759581, DE
    "b198cbb5f8a26147d491dec154ac00e7",  # Campaign 46946007, DE
    "522996e120d8e49ce4fc4dd35be31a54"   # Campaign 46943732, IT
]

def quick_update_project(project_id):
    """Quick update without verification"""
    try:
        url = f"{BASE_URL}/projects/{project_id}"
        headers = {"Authorization": API_KEY}
        data = {
            "auto_scan": 1,
            "times_per_day": 72
        }
        
        response = requests.put(url, headers=headers, data=data, timeout=15)
        if response.status_code == 200:
            result = response.json()
            if result.get('status', {}).get('code') == 'Success':
                return True
        return False
    except:
        return False

def main():
    print("⚡ QUICK UPDATE FOR 8 NEW PROJECTS")
    print("=" * 50)
    
    success_count = 0
    
    for i, project_id in enumerate(new_projects_to_fix, 1):
        print(f"[{i}/8] {project_id[:12]}...", end=" ")
        
        if quick_update_project(project_id):
            success_count += 1
            print("✅ UPDATED")
        else:
            print("❌ FAILED")
        
        time.sleep(0.5)
    
    print(f"\n📊 QUICK RESULTS: {success_count}/8 updated")
    
    if success_count > 0:
        print(f"✅ {success_count} projects updated successfully!")
        print("🔄 Refresh the dashboard to see changes")

if __name__ == "__main__":
    main()