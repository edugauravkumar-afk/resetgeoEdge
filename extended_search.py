import os
import sys
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from dotenv import load_dotenv
import requests
import json

load_dotenv()

# Accounts and expected alert types
ACCOUNT_ALERTS = {
    "1798665": "deceptive site",
    "1413880": "malicious domain", 
    "1929304": "financial scam",
    "1496584": "financial scam",
    "1929287": "malicious cloaking",
    "1929299": "malicious cloaking"
}

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
        
        print(f"Thread {thread_id}: Retrieved {len(alerts)} alerts ({start_date.date()} to {end_date.date()})")
        
        # Search for target accounts and alert types in this batch
        for alert in alerts:
            alert_json = json.dumps(alert, indent=2).lower()
            alert_name = alert.get('alert_name', '').lower()
            trigger_metadata = alert.get('trigger_metadata', '').lower()
            
            for account_id, expected_alert_type in ACCOUNT_ALERTS.items():
                # Check if account ID appears anywhere
                if account_id in alert_json:
                    # Also check if the expected alert type appears
                    alert_type_match = False
                    if expected_alert_type == "deceptive site":
                        alert_type_match = "deceptive" in alert_name or "deceptive" in trigger_metadata
                    elif expected_alert_type == "malicious domain":
                        alert_type_match = "malicious domain" in trigger_metadata
                    elif expected_alert_type == "financial scam":
                        alert_type_match = "financial" in trigger_metadata
                    elif expected_alert_type == "malicious cloaking":
                        alert_type_match = "cloaking" in trigger_metadata
                    
                    with alerts_lock:
                        if account_id not in found_accounts:
                            found_accounts[account_id] = []
                        found_accounts[account_id].append({
                            'thread': thread_id,
                            'alert': alert,
                            'expected_type': expected_alert_type,
                            'alert_type_match': alert_type_match,
                            'actual_alert_name': alert.get('alert_name', ''),
                            'actual_trigger_metadata': alert.get('trigger_metadata', ''),
                            'event_datetime': alert.get('event_datetime', '')
                        })
                        
                        if alert_type_match:
                            print(f"🎯 PERFECT MATCH: {account_id} with {expected_alert_type}!")
                        else:
                            print(f"📍 Found {account_id} but with different alert type: {alert.get('trigger_metadata', '')}")
        
        with alerts_lock:
            all_alerts.extend(alerts)
        
        return alerts
        
    except Exception as e:
        print(f"Thread {thread_id}: Error: {e}")
        return []

def search_extended_timeframe():
    """Search for accounts in extended timeframe."""
    print("🔍 Searching for specific account + alert type combinations")
    print("Expected combinations:")
    for account_id, alert_type in ACCOUNT_ALERTS.items():
        print(f"  {account_id}: {alert_type}")
    
    # Search last 180 days (6 months)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    print(f"\n📅 Searching from {start_date.date()} to {end_date.date()} (180 days)")
    
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
    
    print(f"Using {len(date_ranges)} time chunks")
    
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
    
    print(f"Total alerts searched: {len(all_alerts):,}")
    
    # Report comprehensive findings
    print(f"\n=== COMPREHENSIVE RESULTS ===")
    
    for account_id, expected_alert_type in ACCOUNT_ALERTS.items():
        if account_id in found_accounts:
            findings = found_accounts[account_id]
            perfect_matches = [f for f in findings if f['alert_type_match']]
            other_matches = [f for f in findings if not f['alert_type_match']]
            
            print(f"\n🎯 ACCOUNT {account_id} (Expected: {expected_alert_type}):")
            print(f"   Perfect matches: {len(perfect_matches)}")
            print(f"   Other matches: {len(other_matches)}")
            
            # Show perfect matches first
            if perfect_matches:
                print("   ✅ PERFECT MATCHES:")
                for i, finding in enumerate(perfect_matches[:3], 1):
                    alert = finding['alert']
                    print(f"      #{i}: {alert.get('alert_name', 'Unknown')} | {alert.get('trigger_metadata', 'Unknown')}")
                    print(f"          Date: {alert.get('event_datetime', 'Unknown')}")
                    print(f"          Alert ID: {alert.get('alert_id', 'Unknown')}")
                if len(perfect_matches) > 3:
                    print(f"      ... and {len(perfect_matches) - 3} more perfect matches")
            
            # Show other matches
            if other_matches:
                print("   📋 OTHER MATCHES (different alert types):")
                for i, finding in enumerate(other_matches[:3], 1):
                    alert = finding['alert']
                    print(f"      #{i}: {alert.get('alert_name', 'Unknown')} | {alert.get('trigger_metadata', 'Unknown')}")
                    print(f"          Date: {alert.get('event_datetime', 'Unknown')}")
                if len(other_matches) > 3:
                    print(f"      ... and {len(other_matches) - 3} more other matches")
        else:
            print(f"\n❌ ACCOUNT {account_id}: NO alerts found (Expected: {expected_alert_type})")
    
    # Summary
    total_found = len(found_accounts)
    perfect_matches_count = sum(len([f for f in findings if f['alert_type_match']]) 
                               for findings in found_accounts.values())
    
    print(f"\n=== SUMMARY ===")
    print(f"Accounts searched: {len(ACCOUNT_ALERTS)}")
    print(f"Accounts found: {total_found}")
    print(f"Perfect alert type matches: {perfect_matches_count}")
    print(f"Time period: 180 days ({start_date.date()} to {end_date.date()})")
    
    if total_found < len(ACCOUNT_ALERTS):
        missing = set(ACCOUNT_ALERTS.keys()) - set(found_accounts.keys())
        print(f"Missing accounts: {sorted(missing)}")
        print("These accounts have NO alerts in the 180-day period")

if __name__ == "__main__":
    search_extended_timeframe()