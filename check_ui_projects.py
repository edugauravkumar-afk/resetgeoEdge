#!/usr/bin/env python3
"""
QUICK API CHECK
Verify specific projects from the UI to see their actual API settings
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv("GEOEDGE_API_KEY")
BASE_URL = "https://api.geoedge.com/rest/analytics/v3"

# Projects from the UI screenshot
ui_projects = [
    "42e140410afdf78c69e2f936704a8ee2",  # Campaign 46979603
    "f278d092113c242a1edb5ec7ca0745d6",  # Campaign 46944092
    "7a79aea064afb03185f440910d2351f5",  # Campaign 46612441
    "249b3a10c104798ccc5206048de5b3c7",  # Campaign 46849972
    "9fe55a74951aa644bea24144c7ec6347"   # Campaign 46926843
]

def check_project_api(project_id):
    """Check project via API"""
    url = f"{BASE_URL}/projects/{project_id}"
    headers = {"Authorization": API_KEY}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return {'success': False, 'error': f'HTTP {response.status_code}'}
        
        result = response.json()
        
        if 'response' in result and 'project' in result['response']:
            project = result['response']['project']
            auto_scan = project.get('auto_scan', 0)
            times_per_day = project.get('times_per_day', 0)
            project_name = project.get('name', 'Unknown')
            
            return {
                'success': True,
                'auto_scan': auto_scan,
                'times_per_day': times_per_day,
                'project_name': project_name
            }
        else:
            return {'success': False, 'error': 'Invalid response structure'}
            
    except Exception as e:
        return {'success': False, 'error': str(e)}

def main():
    print("🔍 CHECKING PROJECTS FROM UI SCREENSHOT")
    print("=" * 60)
    
    for i, project_id in enumerate(ui_projects, 1):
        print(f"[{i}/5] {project_id[:12]}...", end=" ")
        
        result = check_project_api(project_id)
        
        if result['success']:
            auto_scan = result['auto_scan']
            times_per_day = result['times_per_day']
            
            if auto_scan == 1 and times_per_day == 72:
                print(f"✅ CORRECT (auto_scan={auto_scan}, times_per_day={times_per_day})")
            else:
                print(f"❌ WRONG (auto_scan={auto_scan}, times_per_day={times_per_day})")
                print(f"     Name: {result['project_name']}")
        else:
            print(f"⚠️ ERROR: {result['error']}")
    
    print(f"\n🤔 CONCLUSION:")
    print(f"If API shows correct values but UI shows 0/0, then:")
    print(f"- Dashboard might be using cached data")
    print(f"- Database might not be updated yet")
    print(f"- There might be a delay in data synchronization")

if __name__ == "__main__":
    main()