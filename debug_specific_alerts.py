import os
import sys
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from dotenv import load_dotenv
import requests

load_dotenv()

# Specific accounts to debug
DEBUG_ACCOUNTS = ["1798665", "1413880", "1929304", "1496584", "1929287", "1929299"]

# Thread-safe collections
alerts_lock = threading.Lock()
all_alerts = []

def _env_or_fail(key: str) -> str:
    value = os.getenv(key, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return value

def fetch_alerts_chunk_direct_api(start_date: datetime, end_date: datetime, 
                                 thread_id: int):
    """Fetch alerts for a specific time chunk using direct API calls."""
    print(f"Thread {thread_id}: Fetching alerts from {start_date.date()} to {end_date.date()}")
    
    try:
        # Get API credentials
        api_key = _env_or_fail("GEOEDGE_API_KEY")
        base_url = _env_or_fail("GEOEDGE_API_BASE").rstrip("/")
        
        # Format dates for API (yyyy-mm-dd hh:mm:ss format as expected)
        start_str = start_date.strftime("%Y-%m-%d 00:00:00")
        end_str = end_date.strftime("%Y-%m-%d 23:59:59")
        
        # Prepare API request
        url = f"{base_url}/alerts/history"
        headers = {
            "Authorization": api_key,
            "Content-Type": "application/json"
        }
        
        alerts = []
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
            session.mount('https://', requests.adapters.HTTPAdapter(max_retries=3))
            
            response = session.get(url, headers=headers, params=params, timeout=60)
            response.raise_for_status()
            
            data = response.json()
            
            # Handle both direct response and wrapped response formats
            if "alerts" in data:
                batch_alerts = data["alerts"]
            elif "response" in data and isinstance(data["response"], dict) and "alerts" in data["response"]:
                batch_alerts = data["response"]["alerts"]
            else:
                break
            
            if not batch_alerts:
                break
            
            alerts.extend(batch_alerts)
            
            # Check if there are more pages
            if "next_page" not in data or not data["next_page"]:
                break
                
            offset += len(batch_alerts)
            
            # If we got less than requested, we're at the end
            if len(batch_alerts) < limit:
                break
        
        print(f"Thread {thread_id}: Retrieved {len(alerts)} total alerts")
        
        # Thread-safe addition to global list
        with alerts_lock:
            all_alerts.extend(alerts)
        
        return alerts
        
    except Exception as e:
        print(f"Thread {thread_id}: Error fetching alerts: {e}")
        return []

def debug_specific_alerts():
    """Debug function to find specific alerts."""
    print("🔍 DEBUG: Searching for specific alert types and accounts")
    
    # Fetch last 90 days of alerts
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    # Split into 7-day chunks
    chunk_days = 7
    date_ranges = []
    current_start = start_date
    thread_id = 0
    
    while current_start < end_date:
        chunk_end = min(current_start + timedelta(days=chunk_days), end_date)
        date_ranges.append((current_start, chunk_end, thread_id))
        current_start = chunk_end
        thread_id += 1
    
    # Fetch alerts
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(fetch_alerts_chunk_direct_api, start, end, tid)
            for start, end, tid in date_ranges
        ]
        
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"Thread failed: {e}")
    
    print(f"Total alerts: {len(all_alerts)}")
    
    # Search for specific alert types
    target_alerts = {
        "deceptive": [],
        "malicious_domain": [],
        "financial": [],
        "cloaking": []
    }
    
    for alert in all_alerts:
        alert_name = alert.get('alert_name', '').lower()
        trigger_metadata = alert.get('trigger_metadata', '').lower()
        full_alert_str = str(alert).lower()
        
        # Check for specific types
        if 'deceptive' in alert_name or 'deceptive' in trigger_metadata:
            target_alerts["deceptive"].append(alert)
        
        if 'malicious domain' in trigger_metadata:
            target_alerts["malicious_domain"].append(alert)
            
        if 'financial' in trigger_metadata:
            target_alerts["financial"].append(alert)
            
        if 'cloaking' in trigger_metadata:
            target_alerts["cloaking"].append(alert)
    
    # Print findings
    for alert_type, alerts in target_alerts.items():
        print(f"\n🚨 Found {len(alerts)} {alert_type.upper()} alerts:")
        
        for i, alert in enumerate(alerts[:10]):  # Show first 10
            print(f"  Alert {i+1}:")
            print(f"    Alert Name: {alert.get('alert_name', 'Unknown')}")
            print(f"    Trigger Metadata: {alert.get('trigger_metadata', 'Unknown')}")
            print(f"    Event DateTime: {alert.get('event_datetime', 'Unknown')}")
            
            # Check if any debug accounts are mentioned
            alert_str = str(alert)
            found_accounts = [acc for acc in DEBUG_ACCOUNTS if acc in alert_str]
            if found_accounts:
                print(f"    🎯 CONTAINS TARGET ACCOUNTS: {found_accounts}")
                print(f"    Full alert data: {alert}")
            print()
            
        if len(alerts) > 10:
            print(f"    ... and {len(alerts) - 10} more alerts")

if __name__ == "__main__":
    debug_specific_alerts()