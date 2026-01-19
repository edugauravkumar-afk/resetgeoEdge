#!/usr/bin/env python3
"""
TARGETED UPDATE FOR UI PROJECTS
Update specific projects visible in UI that are showing 0/0
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

# Projects from UI showing 0/0 that need updating
ui_projects_showing_zero = [
    # First batch (already updated)
    "3649d71904c6cde3eebd066da16a3855",  # Campaign 47003027, ES, 2025-10-21 18:13:28
    "c9c85ea80ebbc4494740ec23fc3c0e2f",  # Campaign 46931844, FR, 2025-10-21 18:13:28
    "a2e31ee433cfa2fe1af7ab161ef90cdf",  # Campaign 44356812, ES, 2025-10-21 18:13:28
    "ab967418cfba6c71636cf641a55417ff",  # Campaign 47001421, ES, 2025-10-21 18:13:28
    "c0358effb8525bf01844a890703b5382",  # Campaign 46982325, DE, 2025-10-21 18:13:28
    "754c85e3cc96116604a4e877a277f867",  # Campaign 46339966, DE, 2025-10-21 18:13:28
    "e7f9f7a52b1a836cb6b7a59fcb3fc083",  # Campaign 46998656, DE,AT,CH, 2025-10-21 18:13:28
    
    # Second batch - newly discovered projects with 0/0
    "6196a9342532dff7f78dab576414ce8a",  # Campaign 46943736, DE, 21/10/25 18:13
    "4c366ca963ca77ab05132c461621b651",  # Campaign 47000620, DE, 21/10/25 18:13
    "abf711007bdc0deff8e97314709014e5",  # Campaign 46951962, DE, 21/10/25 18:13
    "1d850c67696722a63203befc5dfab77a",  # Campaign 46943036, DE, 21/10/25 18:13
    "ce331161cab4bb0af318508399d45fbc",  # Campaign 47004327, DE, 21/10/25 18:13
    "817ceade7ede1943bef541286245c3c2",  # Campaign 46759581, DE, 21/10/25 18:13
    "b198cbb5f8a26147d491dec154ac00e7",  # Campaign 46946007, DE, 21/10/25 18:13
    "522996e120d8e49ce4fc4dd35be31a54"   # Campaign 46943732, IT, 21/10/25 18:13
]

def check_and_update_project(project_id):
    """Check project status and update if needed"""
    print(f"🔍 Checking {project_id[:12]}...", end=" ")
    
    # First check current status
    url = f"{BASE_URL}/projects/{project_id}"
    headers = {"Authorization": API_KEY}
    
    try:
        # GET current status
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"❌ GET ERROR: HTTP {response.status_code}")
            return False
        
        result = response.json()
        
        if 'response' in result and 'project' in result['response']:
            project = result['response']['project']
            auto_scan = project.get('auto_scan', 0)
            times_per_day = project.get('times_per_day', 0)
            project_name = project.get('name', 'Unknown')
            
            print(f"Current: ({auto_scan}/{times_per_day})", end=" ")
            
            # Check if update needed
            if auto_scan == 1 and times_per_day == 72:
                print(f"✅ ALREADY CORRECT")
                return True
            
            # Update the project
            print(f"→ UPDATING...", end=" ")
            update_data = {
                "auto_scan": 1,
                "times_per_day": 72
            }
            
            update_response = requests.put(url, headers=headers, data=update_data, timeout=15)
            if update_response.status_code != 200:
                print(f"❌ PUT ERROR: HTTP {update_response.status_code}")
                return False
            
            update_result = update_response.json()
            
            if update_result.get('status', {}).get('code') == 'Success':
                # Verify the update
                print(f"→ VERIFYING...", end=" ")
                time.sleep(2)  # Wait for update to process
                
                verify_response = requests.get(url, headers=headers, timeout=10)
                if verify_response.status_code == 200:
                    verify_result = verify_response.json()
                    if 'response' in verify_result and 'project' in verify_result['response']:
                        verify_project = verify_result['response']['project']
                        new_auto_scan = verify_project.get('auto_scan', 0)
                        new_times_per_day = verify_project.get('times_per_day', 0)
                        
                        if new_auto_scan == 1 and new_times_per_day == 72:
                            print(f"✅ SUCCESS ({new_auto_scan}/{new_times_per_day})")
                            return True
                        else:
                            print(f"❌ VERIFICATION FAILED ({new_auto_scan}/{new_times_per_day})")
                            return False
                
                print(f"❌ VERIFICATION ERROR")
                return False
            else:
                print(f"❌ UPDATE FAILED: {update_result}")
                return False
        else:
            print(f"❌ INVALID RESPONSE")
            return False
            
    except Exception as e:
        print(f"❌ EXCEPTION: {str(e)}")
        return False

def main():
    print("🎯 TARGETED UPDATE FOR UI PROJECTS SHOWING 0/0")
    print("=" * 60)
    print(f"Updating {len(ui_projects_showing_zero)} projects from UI screenshot")
    print("=" * 60)
    
    success_count = 0
    
    for i, project_id in enumerate(ui_projects_showing_zero, 1):
        print(f"[{i}/{len(ui_projects_showing_zero)}] ", end="")
        
        if check_and_update_project(project_id):
            success_count += 1
        
        time.sleep(1)  # Small delay between updates
    
    print("\n" + "=" * 60)
    print(f"📊 RESULTS:")
    print(f"   ✅ Successfully updated: {success_count}/{len(ui_projects_showing_zero)}")
    print(f"   🎯 Success rate: {(success_count/len(ui_projects_showing_zero)*100):.1f}%")
    
    if success_count == len(ui_projects_showing_zero):
        print(f"\n🎉 ALL UI PROJECTS SUCCESSFULLY UPDATED!")
        print(f"   Refresh the dashboard to see the changes")
    else:
        print(f"\n⚠️ SOME PROJECTS NEED ATTENTION")
        print(f"   {len(ui_projects_showing_zero) - success_count} projects failed to update")

if __name__ == "__main__":
    main()