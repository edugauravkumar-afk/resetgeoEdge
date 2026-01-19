#!/usr/bin/env python3
"""
Update specific projects that were not updated
"""

import requests
import os
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_KEY = os.getenv("GEOEDGE_API_KEY")
BASE_URL = "https://api.geoedge.com/rest/analytics/v3"

# Projects to update (project_id, campaign_id)
PROJECTS_TO_UPDATE = [
    ("a383573ffbb52915b42e1aebbc68d6b4", "46982325"),
    ("9500c0d948d64f325de0667e51574a00", "46838711"),
    ("d8a9791a125c6be7bc10ec50254fcd74", "46521702"),
    ("f5f9da3bd70ba5bb5d781f1d7bf90a7d", "46781298"),
    ("125c017d5487b916f62ba18569c99b7d", "46917494"),
    ("b606a150d419bd91598fa85042bf1249", "46979033"),
    ("cf7035f399da3493d12d0dea56e9b96b", "46954741"),
    ("f57e76a2ea66e18d75d45e2dabd12026", "46932357"),
    ("3c985d2dbfb61cac803e5ab4f6a0048a", "40348250"),
    ("566652d56aa99de83554748bff504677", "46943732"),
    ("f1b4b6a907b0d09514fddef257d5e3b1", "46951995"),
    ("e60ad9b02569afc230d88d24f0c2a686", "46925963"),
    ("d0a517522280fa8f1915b29399c4e15c", "46944092"),
    ("ae0047b9214de835555cd869cd34bc7c", "46766181"),
    ("5d32a755de7b0d03fe37afdcad9dd349", "46999696"),
    ("98524d87472b4628b8e0db743d4f4e03", "46713946"),
]

def get_project_status(project_id):
    """Get current project configuration"""
    try:
        url = f"{BASE_URL}/projects/{project_id}"
        headers = {"Authorization": API_KEY}
        
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            result = response.json()
            if 'response' in result and 'project' in result['response']:
                project = result['response']['project']
                
                auto_scan = int(project.get('auto_scan', 0))
                times_per_day = int(project.get('times_per_day', 0))
                
                return {
                    'success': True,
                    'auto_scan': auto_scan,
                    'times_per_day': times_per_day,
                    'name': project.get('name', 'Unknown')
                }
        
        return {'success': False, 'error': f'HTTP {response.status_code}'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def update_project(project_id, auto_scan=1, times_per_day=72):
    """Update project configuration"""
    try:
        url = f"{BASE_URL}/projects/{project_id}"
        headers = {"Authorization": API_KEY, "Content-Type": "application/json"}
        
        data = {
            "auto_scan": auto_scan,
            "times_per_day": times_per_day
        }
        
        response = requests.put(url, headers=headers, json=data, timeout=15)
        if response.status_code == 200:
            result = response.json()
            success = result.get('status', {}).get('code') == 'Success'
            return {'success': success, 'response': result}
        
        return {'success': False, 'error': f'HTTP {response.status_code}', 'response': response.text}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def main():
    print("=" * 80)
    print("UPDATING SPECIFIC PROJECTS")
    print("=" * 80)
    print(f"\nTotal projects to update: {len(PROJECTS_TO_UPDATE)}\n")
    
    results = {
        'checked': 0,
        'already_correct': 0,
        'updated': 0,
        'failed': 0,
        'verification_passed': 0,
        'verification_failed': 0
    }
    
    for i, (project_id, campaign_id) in enumerate(PROJECTS_TO_UPDATE, 1):
        print(f"\n[{i}/{len(PROJECTS_TO_UPDATE)}] Processing project: {project_id}")
        print(f"    Campaign ID: {campaign_id}")
        
        # Step 1: Check current status
        print("    ├─ Checking current configuration...")
        status = get_project_status(project_id)
        results['checked'] += 1
        
        if not status['success']:
            print(f"    ├─ ❌ Failed to check: {status.get('error', 'Unknown error')}")
            results['failed'] += 1
            continue
        
        current_auto_scan = status['auto_scan']
        current_times_per_day = status['times_per_day']
        
        print(f"    ├─ Current: auto_scan={current_auto_scan}, times_per_day={current_times_per_day}")
        
        # Check if already correct
        if current_auto_scan == 1 and current_times_per_day == 72:
            print("    └─ ✅ Already correctly configured!")
            results['already_correct'] += 1
            continue
        
        # Step 2: Update project
        print("    ├─ Updating to auto_scan=1, times_per_day=72...")
        update_result = update_project(project_id, 1, 72)
        
        if not update_result['success']:
            print(f"    ├─ ❌ Update failed: {update_result.get('error', 'Unknown error')}")
            results['failed'] += 1
            continue
        
        print("    ├─ ✓ Update request successful")
        results['updated'] += 1
        
        # Step 3: Wait and verify
        print("    ├─ Waiting 2 seconds before verification...")
        time.sleep(2)
        
        print("    ├─ Verifying update...")
        verify_status = get_project_status(project_id)
        
        if not verify_status['success']:
            print(f"    ├─ ⚠️  Verification check failed: {verify_status.get('error', 'Unknown error')}")
            results['verification_failed'] += 1
            continue
        
        new_auto_scan = verify_status['auto_scan']
        new_times_per_day = verify_status['times_per_day']
        
        print(f"    ├─ Verified: auto_scan={new_auto_scan}, times_per_day={new_times_per_day}")
        
        if new_auto_scan == 1 and new_times_per_day == 72:
            print("    └─ ✅ UPDATE VERIFIED SUCCESSFULLY!")
            results['verification_passed'] += 1
        else:
            print("    └─ ❌ VERIFICATION FAILED - Values don't match expected!")
            results['verification_failed'] += 1
        
        # Rate limiting delay
        if i < len(PROJECTS_TO_UPDATE):
            time.sleep(0.5)
    
    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total Projects Checked:     {results['checked']}")
    print(f"Already Correct:            {results['already_correct']}")
    print(f"Updated:                    {results['updated']}")
    print(f"Failed to Update:           {results['failed']}")
    print(f"Verification Passed:        {results['verification_passed']}")
    print(f"Verification Failed:        {results['verification_failed']}")
    print("=" * 80)
    
    # Success rate
    if results['updated'] > 0:
        success_rate = (results['verification_passed'] / results['updated']) * 100
        print(f"\nUpdate Success Rate: {success_rate:.1f}%")
    
    if results['verification_passed'] == results['updated']:
        print("\n🎉 ALL UPDATES VERIFIED SUCCESSFULLY!")
        return 0
    else:
        print("\n⚠️  Some updates could not be verified")
        return 1

if __name__ == "__main__":
    exit(main())
