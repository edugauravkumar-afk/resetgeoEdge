#!/usr/bin/env python3
"""
Test GeoEdge API Key
Quick test to verify the API key is working before running the bulk reset
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEOEDGE_API_KEY")
BASE_URL = os.getenv("GEOEDGE_API_BASE", "https://api.geoedge.com/rest/analytics/v3")

def test_api_key():
    """Test if the GeoEdge API key is working"""
    print("🔑 TESTING GEOEDGE API KEY")
    print("=" * 50)
    
    if not API_KEY:
        print("❌ GEOEDGE_API_KEY not found in environment")
        return False
    
    print(f"🔐 API Key: {API_KEY[:8]}...{API_KEY[-8:]} (masked)")
    print(f"🌐 Base URL: {BASE_URL}")
    print()
    
    # Test API with a simple request (try to get projects list)
    test_url = f"{BASE_URL}/projects"
    headers = {"Authorization": API_KEY}
    
    print("🧪 Testing API connection...")
    
    try:
        response = requests.get(test_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            print("✅ API KEY IS WORKING!")
            data = response.json()
            if 'response' in data and 'projects' in data['response']:
                project_count = len(data['response']['projects'])
                print(f"📊 Found {project_count} projects accessible with this API key")
                if project_count > 0:
                    print("🎯 Sample project:", data['response']['projects'][0]['name'][:50] + "...")
            return True
            
        elif response.status_code == 401:
            print("❌ API KEY IS INVALID (401 Unauthorized)")
            print("🔧 Please check your GEOEDGE_API_KEY in .env file")
            return False
            
        elif response.status_code == 403:
            print("❌ API KEY HAS INSUFFICIENT PERMISSIONS (403 Forbidden)")
            return False
            
        else:
            print(f"⚠️ UNEXPECTED RESPONSE: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            return False
            
    except requests.exceptions.Timeout:
        print("⏰ REQUEST TIMED OUT - API might be slow")
        return False
        
    except requests.exceptions.ConnectionError:
        print("🌐 CONNECTION ERROR - Check internet connection")
        return False
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False

def main():
    success = test_api_key()
    
    print()
    print("=" * 50)
    
    if success:
        print("🎉 API KEY TEST SUCCESSFUL!")
        print("✅ Ready to proceed with bulk reset operation")
        print("🚀 You can now run: python reset_inactive_to_manual.py")
    else:
        print("🚨 API KEY TEST FAILED!")
        print("❌ Cannot proceed with bulk reset until API key is fixed")
        print("🔧 Please verify your GEOEDGE_API_KEY in .env file")

if __name__ == "__main__":
    main()