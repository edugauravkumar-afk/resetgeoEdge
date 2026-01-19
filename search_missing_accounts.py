import os
import sys
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from dotenv import load_dotenv
import requests
import json

load_dotenv()

# Specific accounts to find
MISSING_ACCOUNTS = ["1929304", "1496584", "1929287", "1929299", "1798665"]

# Thread-safe collections
alerts_lock = threading.Lock()
all_alerts = []
found_accounts = {}

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
        
        # Format dates for API
        start_str = start_date.strftime("%Y-%m-%d 00:00:00")
        end_str = end_date.strftime("%Y-%m-%d 23:59:59")
        
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
            
            alerts.extend(batch_alerts)
            
            if "next_page" not in data or not data["next_page"]:
                break
                
            offset += len(batch_alerts)
            if len(batch_alerts) < limit:
                break
        
        print(f"Thread {thread_id}: Retrieved {len(alerts)} total alerts")
        
        # Search for missing accounts in this batch
        for alert in alerts:
            alert_json = json.dumps(alert, indent=2)
            for account_id in MISSING_ACCOUNTS:
                if account_id in alert_json:
                    with alerts_lock:
                        if account_id not in found_accounts:
                            found_accounts[account_id] = []
                        found_accounts[account_id].append({
                            'thread': thread_id,
                            'alert': alert,
                            'found_in': 'full_json'
                        })
                        print(f"🎯 FOUND {account_id} in thread {thread_id}!")
        
        with alerts_lock:
            all_alerts.extend(alerts)
        
        return alerts
        
    except Exception as e:
        print(f"Thread {thread_id}: Error fetching alerts: {e}")
        return []

def search_for_missing_accounts():
    """Search for specific missing accounts."""
    print("🔍 Searching for missing accounts in all alerts")
    
    # Fetch alerts from last 90 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    # Split into chunks
    chunk_days = 7
    date_ranges = []
    current_start = start_date
    thread_id = 0
    
    while current_start < end_date:
        chunk_end = min(current_start + timedelta(days=chunk_days), end_date)
        date_ranges.append((current_start, chunk_end, thread_id))
        current_start = chunk_end
        thread_id += 1
    
    print(f"Searching in {len(date_ranges)} time chunks for accounts: {MISSING_ACCOUNTS}")
    
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
    
    print(f"Total alerts searched: {len(all_alerts)}")
    
    # Report findings
    print(f"\n=== SEARCH RESULTS ===")
    if found_accounts:
        for account_id, findings in found_accounts.items():
            print(f"\n🎯 ACCOUNT {account_id} FOUND in {len(findings)} alerts:")
            for i, finding in enumerate(findings[:3]):  # Show first 3
                alert = finding['alert']
                print(f"  Finding #{i+1}:")
                print(f"    Alert Name: {alert.get('alert_name', 'Unknown')}")
                print(f"    Trigger Metadata: {alert.get('trigger_metadata', 'Unknown')}")
                print(f"    Event DateTime: {alert.get('event_datetime', 'Unknown')}")
                print(f"    Alert ID: {alert.get('alert_id', 'Unknown')}")
                
                # Show the relevant part of the alert
                if 'project_name' in alert:
                    print(f"    Project Names: {alert['project_name']}")
                if 'alert_details_url' in alert:
                    print(f"    Alert URL: {alert['alert_details_url']}")
                print()
            
            if len(findings) > 3:
                print(f"    ... and {len(findings) - 3} more findings")
    else:
        print("❌ NONE of the missing accounts were found in any alerts")
        print(f"Searched accounts: {MISSING_ACCOUNTS}")
        print(f"This means these accounts either:")
        print(f"  1. Have no alerts in the last 90 days")
        print(f"  2. Are referenced differently in the system")
        print(f"  3. The alerts exist but use different account ID formats")
    
    # Double-check with broader search
    print(f"\n=== BROADER PATTERN SEARCH ===")
    partial_matches = {}
    for alert in all_alerts[:1000]:  # Check first 1000 alerts for patterns
        alert_str = str(alert).lower()
        for account_id in MISSING_ACCOUNTS:
            # Look for partial matches
            account_partial = account_id[2:]  # Remove first 2 digits
            if account_partial in alert_str:
                if account_id not in partial_matches:
                    partial_matches[account_id] = []
                partial_matches[account_id].append(alert)
    
    if partial_matches:
        print("Found partial matches:")
        for account_id, alerts in partial_matches.items():
            print(f"  {account_id}: {len(alerts)} potential matches")
    else:
        print("No partial matches found either")

if __name__ == "__main__":
    search_for_missing_accounts()