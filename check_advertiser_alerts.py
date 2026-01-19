#!/usr/bin/env python3
"""Check for alerts for specific advertisers in the last 90 days."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Tuple
from collections import defaultdict

import pymysql
from pymysql import MySQLError
from dotenv import load_dotenv

# Import the GeoEdge client
from geoedge_projects.client import GeoEdgeClient

load_dotenv()

# Target advertiser IDs to check
TARGET_ADVERTISERS = [
    "1790942", "1906171", "1413880", "1627055", "1790070", "1892241", "1830732",
    "1180902", "1819766", "1800364", "1795625", "1893748", "1798665", "1895958",
    "1675720", "1929304", "1923113", "1496584", "1929287", "1425690", "1927701",
    "1279600", "1905236", "1793447", "1817514", "1443633", "1885711", "1893748",
    "1895960", "1903778", "1933684", "1798931", "1929299", "1858379", "1906170",
    "1883417", "1920194"
]


def _env_or_fail(key: str) -> str:
    """Get environment variable or raise error if missing."""
    value = os.getenv(key, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return value


def get_db_connection():
    """Create database connection."""
    host = _env_or_fail("MYSQL_HOST")
    port = int(os.getenv("MYSQL_PORT", "3306"))
    user = _env_or_fail("MYSQL_USER")
    password = _env_or_fail("MYSQL_PASSWORD")
    database = _env_or_fail("MYSQL_DB")
    
    return pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        cursorclass=pymysql.cursors.DictCursor,
    )


def get_advertiser_campaigns(advertiser_ids: List[str]) -> Dict[str, List[str]]:
    """Get campaign IDs for each advertiser."""
    if not advertiser_ids:
        return {}

    unique_ids = sorted({int(adv_id) for adv_id in set(advertiser_ids) if str(adv_id).isdigit()})
    if not unique_ids:
        return {}

    placeholders = ", ".join(["%s"] * len(unique_ids))
    
    sql = f"""
        SELECT id as campaign_id, syndicator_id as advertiser_id
        FROM trc.sp_campaigns
        WHERE syndicator_id IN ({placeholders})
    """

    try:
        connection = get_db_connection()
        
        with connection.cursor() as cursor:
            cursor.execute(sql, tuple(unique_ids))
            results = cursor.fetchall()
            
        # Group campaigns by advertiser
        advertiser_campaigns = defaultdict(list)
        for row in results:
            advertiser_id = str(row['advertiser_id'])
            campaign_id = str(row['campaign_id'])
            advertiser_campaigns[advertiser_id].append(campaign_id)
            
        return dict(advertiser_campaigns)
        
    except MySQLError as exc:
        print(f"MySQL error while getting campaigns: {exc}")
        return {}
    finally:
        if 'connection' in locals():
            connection.close()


def check_advertiser_alerts_via_api(advertiser_ids: List[str], days: int = 90) -> Dict[str, Dict[str, Any]]:
    """Check for alerts for specific advertisers using GeoEdge API."""
    try:
        client = GeoEdgeClient()
    except Exception as e:
        print(f"❌ Failed to initialize GeoEdge client: {e}")
        return {}

    # Calculate date range
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)
    
    min_datetime = start_date.strftime("%Y-%m-%d %H:%M:%S")
    max_datetime = now.strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"📅 Fetching alerts from {min_datetime} to {max_datetime}")
    
    # Get campaigns for each advertiser
    advertiser_campaigns = get_advertiser_campaigns(advertiser_ids)
    if not advertiser_campaigns:
        print("❌ No campaigns found for any advertisers")
        return {}
    
    print(f"📊 Found campaigns for {len(advertiser_campaigns)} advertisers")
    
    # Create a reverse mapping from campaign to advertiser
    campaign_to_advertiser = {}
    for advertiser_id, campaigns in advertiser_campaigns.items():
        for campaign_id in campaigns:
            campaign_to_advertiser[campaign_id] = advertiser_id
    
    # Initialize results
    results = {}
    for advertiser_id in advertiser_ids:
        results[advertiser_id] = {
            "alert_count": 0,
            "alerts": [],
            "campaign_ids": advertiser_campaigns.get(advertiser_id, []),
            "first_alert_date": None,
            "last_alert_date": None,
            "alert_types": set(),
        }
    
    count = 0
    matched_alerts = 0
    
    try:
        # Fetch alerts from the API
        for alert in client.iter_alerts_history(
            min_datetime=min_datetime,
            max_datetime=max_datetime,
            page_limit=5000,
            max_pages=200
        ):
            count += 1
            if count % 1000 == 0:
                print(f"📊 Processed {count} alerts, found {matched_alerts} matching...")
            
            # Extract campaign ID from alert
            campaign_id = None
            
            # Try to get campaign ID from project name
            project_name_raw = alert.get("project_name", {})
            if isinstance(project_name_raw, dict) and project_name_raw:
                project_name = list(project_name_raw.values())[0]
            else:
                project_name = str(project_name_raw) if project_name_raw else ""
            
            campaign_id = extract_campaign_id_from_project_name(project_name)
            
            # Also try to get it directly from alert if available
            if not campaign_id:
                campaign_id = str(alert.get("campaign_id", ""))
            
            # Check if this campaign belongs to one of our target advertisers
            if campaign_id and campaign_id in campaign_to_advertiser:
                advertiser_id = campaign_to_advertiser[campaign_id]
                matched_alerts += 1
                
                alert_date = alert.get("date", "")
                alert_type = alert.get("alert_name", "")
                
                results[advertiser_id]["alert_count"] += 1
                results[advertiser_id]["alerts"].append(alert)
                results[advertiser_id]["alert_types"].add(alert_type)
                
                # Track date range
                if alert_date:
                    if not results[advertiser_id]["first_alert_date"] or alert_date < results[advertiser_id]["first_alert_date"]:
                        results[advertiser_id]["first_alert_date"] = alert_date
                    if not results[advertiser_id]["last_alert_date"] or alert_date > results[advertiser_id]["last_alert_date"]:
                        results[advertiser_id]["last_alert_date"] = alert_date
                        
        print(f"📊 Scanned {count} total alerts, found {matched_alerts} matching our advertisers")
        
    except Exception as e:
        print(f"❌ Error fetching alerts: {e}")
        return {}
    
    return results


def extract_campaign_id_from_project_name(project_name: str) -> str:
    """Extract campaign ID from project name like 'name_1814810_46932050_more'"""
    if not project_name:
        return ""
    # Pattern: _CAMPAIGNID_ where campaign ID is typically 7-8 digits
    # Usually the second-to-last number before the very long tracking ID
    parts = project_name.split("_")
    numeric_parts = [p.strip() for p in parts if p.strip().isdigit()]
    
    # Campaign IDs are typically 7-8 digits. Usually 2nd or 3rd numeric part
    # and NOT the longest number (which is tracking ID)
    if len(numeric_parts) >= 2:
        # Try the second numeric part if it's 7-8 digits
        for part in numeric_parts[1:]:
            if 7 <= len(part) <= 8:
                return part
    
    # Fallback: return any numeric part that's 7-8 digits
    for part in numeric_parts:
        if 7 <= len(part) <= 8:
            return part
    
    return ""


def get_advertiser_details(advertiser_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """Get advertiser details like name and status."""
    if not advertiser_ids:
        return {}

    unique_ids = sorted({int(adv_id) for adv_id in set(advertiser_ids) if str(adv_id).isdigit()})
    if not unique_ids:
        return {}

    placeholders = ", ".join(["%s"] * len(unique_ids))
    
    sql = f"""
        SELECT 
            p.id as advertiser_id,
            p.status,
            p.country
        FROM trc.publishers p
        WHERE p.id IN ({placeholders})
        ORDER BY p.id
    """

    try:
        connection = get_db_connection()
        
        with connection.cursor() as cursor:
            cursor.execute(sql, tuple(unique_ids))
            results = cursor.fetchall()
            
        return {str(row['advertiser_id']): row for row in results}
        
    except MySQLError as exc:
        print(f"MySQL error while getting advertiser details: {exc}")
        return {}
    finally:
        if 'connection' in locals():
            connection.close()


def main():
    """Main function to check alerts for target advertisers."""
    # Use shorter time range to avoid API timeout
    days = 30  # Reduced from 90 to 30 days
    print(f"Checking alerts for {len(TARGET_ADVERTISERS)} advertisers in the last {days} days...")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print("-" * 80)
    
    # Get advertiser details
    advertiser_details = get_advertiser_details(TARGET_ADVERTISERS)
    print(f"📊 Found details for {len(advertiser_details)} advertisers in database")
    
    # Get alerts data via API
    alerts_data = check_advertiser_alerts_via_api(TARGET_ADVERTISERS, days=days)
    
    # Summary counters
    total_advertisers = len(TARGET_ADVERTISERS)
    advertisers_with_alerts = len([adv for adv, data in alerts_data.items() if data["alert_count"] > 0])
    advertisers_without_alerts = total_advertisers - advertisers_with_alerts
    total_alerts = sum(data["alert_count"] for data in alerts_data.values())
    
    print()
    print("=== ADVERTISER ALERT SUMMARY (Last {} Days) ===".format(days))
    print(f"Total advertisers checked: {total_advertisers}")
    print(f"Advertisers with alerts: {advertisers_with_alerts}")
    print(f"Advertisers without alerts: {advertisers_without_alerts}")
    print(f"Total alerts found: {total_alerts}")
    print()
    
    if advertisers_with_alerts > 0:
        print("=== ADVERTISERS WITH ALERTS ===")
        for adv_id in TARGET_ADVERTISERS:
            if adv_id in alerts_data and alerts_data[adv_id]["alert_count"] > 0:
                data = alerts_data[adv_id]
                details = advertiser_details.get(adv_id, {})
                
                print(f"Advertiser ID: {adv_id}")
                print(f"  Account Status: {details.get('status', 'N/A')}")
                print(f"  Country: {details.get('country', 'N/A')}")
                print(f"  Campaign Count: {len(data['campaign_ids'])}")
                print(f"  Alert Count: {data['alert_count']}")
                print(f"  First Alert: {data['first_alert_date']}")
                print(f"  Last Alert: {data['last_alert_date']}")
                print(f"  Alert Types: {', '.join(sorted(data['alert_types']))}")
                print("-" * 40)
    
    # Show advertisers without alerts
    advertisers_without_alerts_list = []
    for adv_id in TARGET_ADVERTISERS:
        if adv_id not in alerts_data or alerts_data[adv_id]["alert_count"] == 0:
            advertisers_without_alerts_list.append(adv_id)
    
    if advertisers_without_alerts_list:
        print("\n=== ADVERTISERS WITHOUT ALERTS ===")
        for adv_id in advertisers_without_alerts_list:
            details = advertiser_details.get(adv_id, {})
            campaigns = alerts_data.get(adv_id, {}).get("campaign_ids", [])
            
            print(f"Advertiser ID: {adv_id}")
            print(f"  Account Status: {details.get('status', 'N/A')}")
            print(f"  Country: {details.get('country', 'N/A')}")
            print(f"  Campaign Count: {len(campaigns)}")
            print(f"  Account Created: {details.get('account_created_date', 'N/A')}")
            print("-" * 30)
    
    # Additional detailed breakdown by alert type
    if advertisers_with_alerts > 0:
        print("\n=== ALERT TYPE BREAKDOWN ===")
        alert_type_counts = {}
        for data in alerts_data.values():
            for alert_type in data["alert_types"]:
                alert_type_counts[alert_type] = alert_type_counts.get(alert_type, 0) + 1
        
        for alert_type, count in sorted(alert_type_counts.items()):
            print(f"  {alert_type}: {count}")
    
    print(f"\nCompleted at: {datetime.now(timezone.utc).isoformat()}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)