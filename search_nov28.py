import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests
import json

load_dotenv()

def _env_or_fail(key: str) -> str:
    value = os.getenv(key, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return value

def search_specific_date_range():
    """Search for account 1798665 around Nov 28, 2025."""
    print("🔍 Searching for account 1798665 around Nov 28, 2025")
    
    # Search Nov 25-30, 2025
    start_date = datetime(2025, 11, 25)
    end_date = datetime(2025, 11, 30)
    
    print(f"Search period: {start_date.date()} to {end_date.date()}")
    
    try:
        api_key = _env_or_fail("GEOEDGE_API_KEY")
        base_url = _env_or_fail("GEOEDGE_API_BASE").rstrip("/")
        
        start_str = start_date.strftime("%Y-%m-%d 00:00:00")
        end_str = end_date.strftime("%Y-%m-%d 23:59:59")
        
        url = f"{base_url}/alerts/history"
        headers = {
            "Authorization": api_key,
            "Content-Type": "application/json"
        }
        
        all_alerts = []
        offset = 0
        limit = 5000
        
        while True:
            params = {
                "min_datetime": start_str,
                "max_datetime": end_str,
                "offset": offset,
                "limit": limit,
                "full_raw": 1
            }
            
            session = requests.Session()
            response = session.get(url, headers=headers, params=params, timeout=60)
            response.raise_for_status()
            data = response.json()
            
            if "alerts" in data:
                batch_alerts = data["alerts"]
            elif "response" in data and isinstance(data["response"], dict) and "alerts" in data["response"]:
                batch_alerts = data["response"]["alerts"]
            else:
                break
            
            if not batch_alerts:
                break
            
            all_alerts.extend(batch_alerts)
            
            if "next_page" not in data or not data["next_page"]:
                break
                
            offset += len(batch_alerts)
            if len(batch_alerts) < limit:
                break
        
        print(f"Retrieved {len(all_alerts)} total alerts in date range")
        
        # Search for account 1798665
        found_alerts_1798665 = []
        deceptive_alerts = []
        
        for alert in all_alerts:
            alert_json = json.dumps(alert, indent=2)
            
            # Check for account 1798665
            if "1798665" in alert_json:
                found_alerts_1798665.append(alert)
            
            # Check for deceptive alerts
            alert_name = alert.get('alert_name', '').lower()
            trigger_metadata = alert.get('trigger_metadata', '').lower()
            if 'deceptive' in alert_name or 'deceptive' in trigger_metadata:
                deceptive_alerts.append(alert)
        
        print(f"\n=== ACCOUNT 1798665 ALERTS ===")
        if found_alerts_1798665:
            print(f"Found {len(found_alerts_1798665)} alerts for account 1798665:")
            for i, alert in enumerate(found_alerts_1798665, 1):
                print(f"\nAlert #{i}:")
                print(f"  Alert Name: {alert.get('alert_name', 'Unknown')}")
                print(f"  Trigger Metadata: {alert.get('trigger_metadata', 'Unknown')}")
                print(f"  Event DateTime: {alert.get('event_datetime', 'Unknown')}")
                print(f"  Alert ID: {alert.get('alert_id', 'Unknown')}")
                print(f"  Project Names: {alert.get('project_name', {})}")
                print(f"  Location: {alert.get('location', {})}")
                print(f"  Alert URL: {alert.get('alert_details_url', 'No URL')}")
        else:
            print("❌ No alerts found for account 1798665 in this date range")
        
        print(f"\n=== ALL DECEPTIVE ALERTS IN DATE RANGE ===")
        if deceptive_alerts:
            print(f"Found {len(deceptive_alerts)} deceptive alerts:")
            for i, alert in enumerate(deceptive_alerts, 1):
                print(f"\nDeceptive Alert #{i}:")
                print(f"  Alert Name: {alert.get('alert_name', 'Unknown')}")
                print(f"  Trigger Metadata: {alert.get('trigger_metadata', 'Unknown')}")
                print(f"  Event DateTime: {alert.get('event_datetime', 'Unknown')}")
                print(f"  Alert ID: {alert.get('alert_id', 'Unknown')}")
                
                # Check if this alert contains 1798665
                alert_json = json.dumps(alert)
                if "1798665" in alert_json:
                    print(f"  🎯 THIS ALERT CONTAINS ACCOUNT 1798665!")
                    print(f"  Project Names: {alert.get('project_name', {})}")
                    print(f"  Location: {alert.get('location', {})}")
                    print(f"  Alert URL: {alert.get('alert_details_url', 'No URL')}")
        else:
            print("❌ No deceptive alerts found in this date range")
        
        # Check Nov 28 specifically
        print(f"\n=== NOV 28, 2025 SPECIFIC CHECK ===")
        nov28_alerts = [alert for alert in all_alerts 
                       if alert.get('event_datetime', '').startswith('2025-11-28')]
        
        print(f"Total alerts on Nov 28, 2025: {len(nov28_alerts)}")
        
        nov28_1798665 = []
        nov28_deceptive = []
        
        for alert in nov28_alerts:
            alert_json = json.dumps(alert)
            if "1798665" in alert_json:
                nov28_1798665.append(alert)
            
            alert_name = alert.get('alert_name', '').lower()
            trigger_metadata = alert.get('trigger_metadata', '').lower()
            if 'deceptive' in alert_name or 'deceptive' in trigger_metadata:
                nov28_deceptive.append(alert)
        
        if nov28_1798665:
            print(f"Account 1798665 alerts on Nov 28: {len(nov28_1798665)}")
            for alert in nov28_1798665:
                print(f"  - {alert.get('alert_name')} | {alert.get('trigger_metadata')} | {alert.get('event_datetime')}")
        
        if nov28_deceptive:
            print(f"Deceptive alerts on Nov 28: {len(nov28_deceptive)}")
            for alert in nov28_deceptive:
                print(f"  - {alert.get('alert_name')} | {alert.get('trigger_metadata')} | {alert.get('event_datetime')}")
                alert_json = json.dumps(alert)
                if "1798665" in alert_json:
                    print(f"    🎯 CONTAINS 1798665!")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    search_specific_date_range()