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

def comprehensive_search_1798665():
    """Comprehensive search for account 1798665 and deceptive alerts."""
    print("🔍 Comprehensive search for account 1798665 and deceptive alerts")
    
    # Search entire November 2025
    start_date = datetime(2025, 11, 1)
    end_date = datetime(2025, 11, 30, 23, 59, 59)
    
    print(f"Search period: {start_date.date()} to {end_date.date()} (Full November 2025)")
    
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
        
        print(f"Retrieved {len(all_alerts)} total alerts in November 2025")
        
        # Find all alerts containing 1798665
        alerts_1798665 = []
        deceptive_alerts = []
        
        for alert in all_alerts:
            alert_json = json.dumps(alert, indent=2)
            
            # Check for account 1798665
            if "1798665" in alert_json:
                alerts_1798665.append(alert)
            
            # Check for deceptive alerts
            alert_name = alert.get('alert_name', '').lower()
            trigger_metadata = alert.get('trigger_metadata', '').lower()
            if 'deceptive' in alert_name or 'deceptive' in trigger_metadata or 'offensive' in alert_name:
                deceptive_alerts.append(alert)
        
        print(f"\n=== ALL ALERTS FOR 1798665 IN NOVEMBER 2025 ===")
        if alerts_1798665:
            print(f"Found {len(alerts_1798665)} alerts for account 1798665:")
            for i, alert in enumerate(alerts_1798665, 1):
                print(f"\nAlert #{i}:")
                print(f"  Alert Name: {alert.get('alert_name', 'Unknown')}")
                print(f"  Trigger Metadata: {alert.get('trigger_metadata', 'Unknown')}")
                print(f"  Event DateTime: {alert.get('event_datetime', 'Unknown')}")
                print(f"  Alert ID: {alert.get('alert_id', 'Unknown')}")
                print(f"  Project Names: {list(alert.get('project_name', {}).values())}")
                print(f"  Location: {alert.get('location', {})}")
                
                # Check if it's deceptive
                alert_name = alert.get('alert_name', '').lower()
                trigger_metadata = alert.get('trigger_metadata', '').lower()
                if 'deceptive' in alert_name or 'deceptive' in trigger_metadata or 'offensive' in alert_name:
                    print(f"  🎯 THIS IS A DECEPTIVE/OFFENSIVE ALERT!")
        else:
            print("❌ No alerts found for account 1798665 in November 2025")
        
        print(f"\n=== ALL DECEPTIVE/OFFENSIVE ALERTS IN NOVEMBER 2025 ===")
        if deceptive_alerts:
            print(f"Found {len(deceptive_alerts)} deceptive/offensive alerts:")
            for i, alert in enumerate(deceptive_alerts, 1):
                print(f"\nDeceptive Alert #{i}:")
                print(f"  Alert Name: {alert.get('alert_name', 'Unknown')}")
                print(f"  Trigger Metadata: {alert.get('trigger_metadata', 'Unknown')}")
                print(f"  Event DateTime: {alert.get('event_datetime', 'Unknown')}")
                
                # Check if this alert contains 1798665
                alert_json = json.dumps(alert)
                if "1798665" in alert_json:
                    print(f"  🎯 THIS ALERT CONTAINS ACCOUNT 1798665!")
                    print(f"  Project Names: {list(alert.get('project_name', {}).values())}")
                    print(f"  Alert URL: {alert.get('alert_details_url', 'No URL')}")
        else:
            print("❌ No deceptive/offensive alerts found in November 2025")
            
        # Also search in the entire time period we've been using (last 90 days)
        print(f"\n=== SEARCHING IN FULL 90-DAY PERIOD FOR DECEPTIVE + 1798665 ===")
        end_date_90 = datetime.now()
        start_date_90 = end_date_90 - timedelta(days=90)
        
        print(f"Searching {start_date_90.date()} to {end_date_90.date()}")
        
        # Quick search in our already fetched alerts if they cover this period
        matching_alerts = []
        for alert in all_alerts:
            alert_json = json.dumps(alert)
            alert_name = alert.get('alert_name', '').lower()
            trigger_metadata = alert.get('trigger_metadata', '').lower()
            
            # Must contain 1798665 AND be deceptive/offensive
            if ("1798665" in alert_json and 
                ('deceptive' in alert_name or 'deceptive' in trigger_metadata or 
                 'offensive' in alert_name)):
                matching_alerts.append(alert)
        
        if matching_alerts:
            print(f"🎯 Found {len(matching_alerts)} alerts that match both 1798665 AND deceptive criteria:")
            for alert in matching_alerts:
                print(f"  - {alert.get('event_datetime')}: {alert.get('alert_name')} | {alert.get('trigger_metadata')}")
        else:
            print("❌ No alerts found that contain both 1798665 and deceptive criteria")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    comprehensive_search_1798665()