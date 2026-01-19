#!/usr/bin/env python3
"""
Diagnose why updates are not working for specific projects
"""

import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEOEDGE_API_KEY")
BASE_URL = "https://api.geoedge.com/rest/analytics/v3"

# Test with first project
TEST_PROJECT_ID = "a383573ffbb52915b42e1aebbc68d6b4"

print("=" * 80)
print("DIAGNOSING UPDATE ISSUE")
print("=" * 80)
print(f"\nTesting with project: {TEST_PROJECT_ID}\n")

# Step 1: Get current status
print("Step 1: Getting current status...")
url = f"{BASE_URL}/projects/{TEST_PROJECT_ID}"
headers = {"Authorization": API_KEY}

response = requests.get(url, headers=headers, timeout=15)
print(f"GET Status Code: {response.status_code}")
print(f"GET Response:")
print(json.dumps(response.json(), indent=2))

current_data = response.json()
if 'response' in current_data and 'project' in current_data['response']:
    project = current_data['response']['project']
    print(f"\nCurrent auto_scan: {project.get('auto_scan')}")
    print(f"Current times_per_day: {project.get('times_per_day')}")

# Step 2: Attempt update
print("\n" + "-" * 80)
print("Step 2: Attempting update...")
headers_update = {"Authorization": API_KEY, "Content-Type": "application/json"}
data = {
    "auto_scan": 1,
    "times_per_day": 72
}

print(f"Update payload: {json.dumps(data, indent=2)}")

response_update = requests.put(url, headers=headers_update, json=data, timeout=15)
print(f"\nPUT Status Code: {response_update.status_code}")
print(f"PUT Response:")
print(json.dumps(response_update.json(), indent=2))

# Step 3: Verify immediately
print("\n" + "-" * 80)
print("Step 3: Verifying immediately after update...")
response_verify = requests.get(url, headers=headers, timeout=15)
print(f"GET Status Code: {response_verify.status_code}")

verify_data = response_verify.json()
if 'response' in verify_data and 'project' in verify_data['response']:
    project = verify_data['response']['project']
    print(f"\nAfter update auto_scan: {project.get('auto_scan')}")
    print(f"After update times_per_day: {project.get('times_per_day')}")
    
    if project.get('auto_scan') == 1 and project.get('times_per_day') == 72:
        print("\n✅ UPDATE SUCCESSFUL!")
    else:
        print("\n❌ UPDATE FAILED - Values not changed")
        print("\nFull project data:")
        print(json.dumps(project, indent=2))

print("\n" + "=" * 80)
