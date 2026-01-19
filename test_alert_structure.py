#!/usr/bin/env python3
"""
Quick test to check alert metadata structure
"""
from geoedge_projects.client import GeoEdgeClient
from datetime import datetime, timedelta
from dotenv import load_dotenv
import json
import signal
import sys

load_dotenv()

def timeout_handler(signum, frame):
    print("\n⏱️  Timeout! API took too long to respond.")
    sys.exit(1)

# Set 60 second timeout
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(60)

try:
    client = GeoEdgeClient()
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=3)  # Just 3 days
    
    print(f"Fetching recent alerts with full metadata (3 day window)...")
    print(f"This may take a minute...\n")
    
    count = 0
    for alert in client.iter_alerts_history(
        min_datetime=start_date.strftime("%Y-%m-%d %H:%M:%S"),
        max_datetime=end_date.strftime("%Y-%m-%d %H:%M:%S"),
        full_raw=1,
        page_limit=10
    ):
        count += 1
        print(f"\n{'='*70}")
        print(f"Alert {count}")
        print(f"{'='*70}")
        print(f"ID: {alert.get('id')}")
        print(f"Name: {alert.get('alert_name')}")
        print(f"DateTime: {alert.get('event_datetime')}")
        
        print(f"\nAll keys in alert: {sorted(alert.keys())}")
        
        # Print full alert structure
        print(f"\nFull alert (first 2000 chars):")
        print(json.dumps(alert, indent=2, default=str)[:2000])
        
        if count >= 3:
            break
    
    signal.alarm(0)  # Cancel alarm
    print(f"\n✅ Successfully fetched {count} alerts")
    
except Exception as e:
    signal.alarm(0)
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
