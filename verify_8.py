#!/usr/bin/env python3
"""
VERIFY THE 8 UPDATED PROJECTS
Check that they now show 1/72
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv("GEOEDGE_API_KEY")
BASE_URL = "https://api.geoedge.com/rest/analytics/v3"

# The 8 projects we just updated
projects_to_verify = [
    "6196a9342532dff7f78dab576414ce8a",  # Campaign 46943736, DE
    "4c366ca963ca77ab05132c461621b651",  # Campaign 47000620, DE
    "abf711007bdc0deff8e97314709014e5",  # Campaign 46951962, DE
    "1d850c67696722a63203befc5dfab77a",  # Campaign 46943036, DE
    "ce331161cab4bb0af318508399d45fbc",  # Campaign 47004327, DE
    "817ceade7ede1943bef541286245c3c2",  # Campaign 46759581, DE
    "b198cbb5f8a26147d491dec154ac00e7",  # Campaign 46946007, DE
    "522996e120d8e49ce4fc4dd35be31a54"   # Campaign 46943732, IT
]

def verify_project(project_id):
    """Verify project settings"""
    try:
        url = f"{BASE_URL}/projects/{project_id}"
        headers = {"Authorization": API_KEY}
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if 'response' in result and 'project' in result['response']:
                project = result['response']['project']
                auto_scan = project.get('auto_scan', 0)
                times_per_day = project.get('times_per_day', 0)
                return auto_scan, times_per_day
        return None, None
    except:
        return None, None

def main():
    print("🔍 VERIFYING 8 UPDATED PROJECTS")
    print("=" * 40)
    
    all_correct = True
    
    for i, project_id in enumerate(projects_to_verify, 1):
        auto_scan, times_per_day = verify_project(project_id)
        
        print(f"[{i}/8] {project_id[:12]}...", end=" ")
        
        if auto_scan == 1 and times_per_day == 72:
            print(f"✅ CORRECT (1/72)")
        elif auto_scan is not None:
            print(f"❌ WRONG ({auto_scan}/{times_per_day})")
            all_correct = False
        else:
            print(f"⚠️ ERROR")
            all_correct = False
    
    print(f"\n📊 VERIFICATION RESULT:")
    if all_correct:
        print(f"🎉 ALL 8 PROJECTS ARE CORRECTLY SET TO 1/72!")
    else:
        print(f"⚠️ Some projects still need fixing")

if __name__ == "__main__":
    main()