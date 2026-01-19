#!/usr/bin/env python3
"""
Debug script to examine the structure of alert data from GeoEdge API
"""

import json
import sys
from datetime import datetime, timedelta
from geoedge_projects.client import GeoEdgeClient

def debug_alert_structure():
    """Fetch a few alerts and examine their structure"""
    try:
        client = GeoEdgeClient()
        
        # Get alerts from the last 7 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        print("🔍 Fetching sample alerts to examine data structure...")
        
        alerts = []
        for alert in client.iter_alerts_history(
            min_datetime=start_date.strftime("%Y-%m-%d %H:%M:%S"),
            max_datetime=end_date.strftime("%Y-%m-%d %H:%M:%S"),
            page_limit=5  # Just get a few for debugging
        ):
            alerts.append(alert)
            if len(alerts) >= 3:  # Just examine 3 alerts
                break
        
        if not alerts:
            print("❌ No alerts found in the last 7 days")
            return
        
        print(f"✅ Found {len(alerts)} sample alerts. Examining structure...")
        print("=" * 80)
        
        for i, alert in enumerate(alerts, 1):
            print(f"\n📋 ALERT {i} STRUCTURE:")
            print("-" * 40)
            
            # Print all top-level keys and their types
            for key, value in alert.items():
                if isinstance(value, dict):
                    print(f"  {key}: dict with keys {list(value.keys())}")
                    # Show nested structure
                    for sub_key, sub_value in value.items():
                        print(f"    └─ {sub_key}: {type(sub_value).__name__} = {sub_value}")
                elif isinstance(value, list):
                    print(f"  {key}: list with {len(value)} items")
                    if value:
                        print(f"    └─ example: {value[0]}")
                else:
                    print(f"  {key}: {type(value).__name__} = {value}")
            
            print("\n🔍 LOOKING FOR CAMPAIGN INFO:")
            # Look for campaign-related fields
            campaign_fields = [k for k in alert.keys() if 'campaign' in k.lower()]
            if campaign_fields:
                print(f"  Campaign fields found: {campaign_fields}")
                for field in campaign_fields:
                    print(f"    {field}: {alert[field]}")
            else:
                print("  No obvious campaign fields found")
            
            print("\n🔍 LOOKING FOR TAG/URL INFO:")
            # Look for tag/URL fields
            tag_fields = [k for k in alert.keys() if any(word in k.lower() for word in ['tag', 'url', 'ad'])]
            if tag_fields:
                print(f"  Tag/URL fields found: {tag_fields}")
                for field in tag_fields:
                    print(f"    {field}: {alert[field]}")
            else:
                print("  No obvious tag/URL fields found")
            
            print("=" * 80)
        
        # Save to file for detailed inspection
        with open('/Users/gaurav.k/Desktop/geoedge-country-projects/sample_alerts.json', 'w') as f:
            json.dump(alerts, f, indent=2, default=str)
        
        print("\n💾 Sample alerts saved to 'sample_alerts.json' for detailed inspection")
        
    except Exception as e:
        print(f"❌ Error examining alert structure: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    debug_alert_structure()