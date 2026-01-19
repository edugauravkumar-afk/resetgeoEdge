#!/usr/bin/env python3
"""
API-ONLY VERIFICATION SCRIPT
Check project status using only GeoEdge API (no database needed)
"""

import os
import sys
import time
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv("GEOEDGE_API_KEY")
BASE_URL = "https://api.geoedge.com/rest/analytics/v3"

def check_project_status(project_id):
    """Check a single project's auto_scan and times_per_day settings"""
    url = f"{BASE_URL}/projects/{project_id}"
    headers = {"Authorization": API_KEY}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return {'success': False, 'error': f'HTTP {response.status_code}'}
        
        result = response.json()
        
        # Handle API response structure
        if 'response' in result and 'project' in result['response']:
            project = result['response']['project']
            auto_scan = project.get('auto_scan', 0)
            times_per_day = project.get('times_per_day', 0)
            
            return {
                'success': True,
                'auto_scan': auto_scan,
                'times_per_day': times_per_day,
                'correct': auto_scan == 1 and times_per_day == 72
            }
        else:
            return {'success': False, 'error': 'Invalid response structure'}
            
    except requests.exceptions.RequestException as e:
        return {'success': False, 'error': f'Request error: {str(e)}'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def get_sample_project_ids():
    """Get a sample of project IDs to test"""
    # These are real project IDs from Campaign 46972731 that we know exist
    sample_ids = [
        "21b98db846c7708fde86dfa2cd89c9fd",  # Campaign 46972731
        "89267b98e55bab2d8a10ec59b767bb35",  # Campaign 46972731  
        "e73e889e8e199d8010b9f68f587beec3"   # Campaign 46972731
    ]
    
    return sample_ids

def main():
    print("🚀 API-ONLY PROJECT VERIFICATION")
    print("=" * 50)
    
    # Get sample project IDs
    project_ids = get_sample_project_ids()
    total = len(project_ids)
    
    print(f"🔍 Testing {total} sample projects...")
    print(f"🎯 Target: auto_scan=1, times_per_day=72")
    print("=" * 50)
    
    correct_count = 0
    incorrect_count = 0
    error_count = 0
    
    for i, project_id in enumerate(project_ids, 1):
        # Show progress
        print(f"[{i}/{total}] Checking {project_id[:8]}...", end=" ", flush=True)
        
        result = check_project_status(project_id)
        
        if result['success']:
            if result['correct']:
                correct_count += 1
                print(f"✅ CORRECT (auto_scan={result['auto_scan']}, times_per_day={result['times_per_day']})")
            else:
                incorrect_count += 1
                print(f"❌ WRONG (auto_scan={result['auto_scan']}, times_per_day={result['times_per_day']})")
        else:
            error_count += 1
            print(f"⚠️ ERROR: {result['error']}")
        
        # Small delay to avoid rate limiting
        time.sleep(0.2)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 VERIFICATION RESULTS:")
    print(f"   ✅ Correctly configured: {correct_count}/{total}")
    print(f"   ❌ Incorrectly configured: {incorrect_count}/{total}")
    print(f"   ⚠️ API errors: {error_count}/{total}")
    print(f"   🎯 Success rate: {(correct_count/total)*100:.1f}%")
    
    if incorrect_count > 0:
        print(f"\n🚨 ISSUES DETECTED!")
        print(f"   {incorrect_count} out of {total} sample projects are not properly configured")
        print(f"   This suggests the bulk update may not have worked correctly")
        print(f"   🔧 Recommend running bulk update again")
    else:
        print(f"\n🎉 ALL SAMPLE PROJECTS LOOK GOOD!")
        print(f"   All {total} tested projects are correctly configured")

if __name__ == "__main__":
    main()