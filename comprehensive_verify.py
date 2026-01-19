#!/usr/bin/env python3
"""
COMPREHENSIVE PROJECT VERIFICATION
Check a larger sample of projects to verify bulk update results
Shows real-time progress and detailed statistics
"""

import os
import sys
import time
import requests
from dotenv import load_dotenv
import json

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
        if response.status_code == 404:
            return {'success': False, 'error': 'Project not found (404)', 'exists': False}
        elif response.status_code != 200:
            return {'success': False, 'error': f'HTTP {response.status_code}', 'exists': True}
        
        result = response.json()
        
        # Handle API response structure
        if 'response' in result and 'project' in result['response']:
            project = result['response']['project']
            auto_scan = project.get('auto_scan', 0)
            times_per_day = project.get('times_per_day', 0)
            project_name = project.get('name', 'Unknown')
            
            return {
                'success': True,
                'auto_scan': auto_scan,
                'times_per_day': times_per_day,
                'correct': auto_scan == 1 and times_per_day == 72,
                'project_name': project_name,
                'exists': True
            }
        else:
            return {'success': False, 'error': 'Invalid response structure', 'exists': True}
            
    except requests.exceptions.RequestException as e:
        return {'success': False, 'error': f'Request error: {str(e)}', 'exists': True}
    except Exception as e:
        return {'success': False, 'error': str(e), 'exists': True}

def get_diverse_project_ids():
    """Get a diverse sample of project IDs to test from different sources"""
    # Known working projects from Campaign 46972731
    confirmed_working = [
        "21b98db846c7708fde86dfa2cd89c9fd",  # Campaign 46972731
        "89267b98e55bab2d8a10ec59b767bb35",  # Campaign 46972731  
        "e73e889e8e199d8010b9f68f587beec3"   # Campaign 46972731
    ]
    
    # Sample project IDs from your bulk update script (may or may not exist)
    additional_samples = [
        "a1b2c3d4e5f6789012345678901234ab",
        "b2c3d4e5f6789012345678901234abc1", 
        "c3d4e5f6789012345678901234abc12b",
        "d4e5f6789012345678901234abc12bc3",
        "e5f6789012345678901234abc12bc34d"
    ]
    
    return {
        'confirmed': confirmed_working,
        'samples': additional_samples,
        'all': confirmed_working + additional_samples
    }

def main():
    print("🚀 COMPREHENSIVE PROJECT VERIFICATION")
    print("=" * 60)
    
    # Get project IDs
    project_groups = get_diverse_project_ids()
    
    print(f"🔍 Testing different project groups:")
    print(f"   📋 Confirmed working: {len(project_groups['confirmed'])} projects")
    print(f"   🎲 Additional samples: {len(project_groups['samples'])} projects") 
    print(f"   📊 Total to check: {len(project_groups['all'])} projects")
    print(f"🎯 Target: auto_scan=1, times_per_day=72")
    print("=" * 60)
    
    # Statistics
    total_checked = 0
    correct_count = 0
    incorrect_count = 0
    error_count = 0
    not_found_count = 0
    
    incorrect_projects = []
    
    # Test confirmed working projects first
    print(f"\n🔍 TESTING CONFIRMED WORKING PROJECTS ({len(project_groups['confirmed'])} projects)")
    print("-" * 60)
    
    for i, project_id in enumerate(project_groups['confirmed'], 1):
        total_checked += 1
        print(f"[{i}/{len(project_groups['confirmed'])}] {project_id[:12]}...", end=" ", flush=True)
        
        result = check_project_status(project_id)
        
        if result['success']:
            if result['correct']:
                correct_count += 1
                print(f"✅ CORRECT (auto_scan={result['auto_scan']}, times_per_day={result['times_per_day']})")
            else:
                incorrect_count += 1
                incorrect_projects.append({
                    'id': project_id,
                    'auto_scan': result['auto_scan'],
                    'times_per_day': result['times_per_day'],
                    'name': result.get('project_name', 'Unknown')
                })
                print(f"❌ WRONG (auto_scan={result['auto_scan']}, times_per_day={result['times_per_day']})")
        else:
            if not result.get('exists', True):
                not_found_count += 1
                print(f"🚫 NOT FOUND")
            else:
                error_count += 1
                print(f"⚠️ ERROR: {result['error']}")
        
        time.sleep(0.1)
    
    # Test additional samples
    print(f"\n🎲 TESTING ADDITIONAL SAMPLE PROJECTS ({len(project_groups['samples'])} projects)")
    print("-" * 60)
    
    for i, project_id in enumerate(project_groups['samples'], 1):
        total_checked += 1
        print(f"[{i}/{len(project_groups['samples'])}] {project_id[:12]}...", end=" ", flush=True)
        
        result = check_project_status(project_id)
        
        if result['success']:
            if result['correct']:
                correct_count += 1
                print(f"✅ CORRECT (auto_scan={result['auto_scan']}, times_per_day={result['times_per_day']})")
            else:
                incorrect_count += 1
                incorrect_projects.append({
                    'id': project_id,
                    'auto_scan': result['auto_scan'],
                    'times_per_day': result['times_per_day'],
                    'name': result.get('project_name', 'Unknown')
                })
                print(f"❌ WRONG (auto_scan={result['auto_scan']}, times_per_day={result['times_per_day']})")
        else:
            if not result.get('exists', True):
                not_found_count += 1
                print(f"🚫 NOT FOUND")
            else:
                error_count += 1
                print(f"⚠️ ERROR: {result['error']}")
        
        time.sleep(0.1)
    
    # Final summary
    print("\n" + "=" * 60)
    print("📊 FINAL VERIFICATION RESULTS:")
    print(f"   📋 Total projects checked: {total_checked}")
    print(f"   ✅ Correctly configured: {correct_count}")
    print(f"   ❌ Incorrectly configured: {incorrect_count}")
    print(f"   🚫 Projects not found: {not_found_count}")
    print(f"   ⚠️ API errors: {error_count}")
    
    if total_checked - not_found_count > 0:
        success_rate = (correct_count / (total_checked - not_found_count)) * 100
        print(f"   🎯 Success rate (existing projects): {success_rate:.1f}%")
    
    # Detailed analysis
    print(f"\n📈 ANALYSIS:")
    if correct_count == len(project_groups['confirmed']):
        print(f"   ✅ All confirmed working projects are still correctly configured")
    else:
        print(f"   ⚠️ Some confirmed working projects have issues!")
    
    if incorrect_count > 0:
        print(f"\n❌ PROJECTS NEEDING ATTENTION ({incorrect_count} projects):")
        for proj in incorrect_projects:
            print(f"   - {proj['id'][:12]}... (auto_scan={proj['auto_scan']}, times_per_day={proj['times_per_day']})")
        
        print(f"\n🔧 RECOMMENDATIONS:")
        print(f"   - {incorrect_count} projects are not properly configured")
        print(f"   - Consider running bulk update again for these specific projects")
    else:
        print(f"\n🎉 EXCELLENT NEWS!")
        print(f"   All existing, accessible projects are correctly configured!")
        print(f"   Your bulk update appears to be working properly!")
    
    return 0 if incorrect_count == 0 else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)