#!/usr/bin/env python3
"""
LATAM & Greater China accounts with English-targeting campaigns having LP alerts in last 24h

Corrected Flow:
1. Find campaigns targeting English countries (US, GB, CA, AU, NZ, IE) in trc.geo_edge_projects
2. Fetch Landing Page alerts from last 24 hours via GeoEdge API
3. Filter for LP change alerts
4. Match to campaigns via trc.geo_edge_landing_pages (advertiser_id = account_id)
5. Fetch account country from trc.publishers
6. Filter for LATAM and Greater China only
7. Output to CSV
"""

import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Set
from collections import defaultdict
import csv

import pymysql
from pymysql import MySQLError
from dotenv import load_dotenv

from geoedge_projects.client import GeoEdgeClient

load_dotenv()

# Regional country codes
ENGLISH_COUNTRIES = {"US", "GB", "CA", "AU", "NZ", "IE"}
LATAM_COUNTRIES = {"MX", "AR", "BR", "CL", "CO", "PE"}
GREATER_CHINA_COUNTRIES = {"CN", "HK", "TW", "MO"}
TARGET_REGIONS = LATAM_COUNTRIES | GREATER_CHINA_COUNTRIES


def _env_or_fail(key: str) -> str:
    value = os.getenv(key, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return value


def fetch_english_targeting_campaigns() -> Dict[str, Dict[str, Any]]:
    """Query campaigns targeting English countries"""
    host = _env_or_fail("MYSQL_HOST")
    port = int(os.getenv("MYSQL_PORT", "3306"))
    user = _env_or_fail("MYSQL_USER")
    password = _env_or_fail("MYSQL_PASSWORD")
    database = _env_or_fail("MYSQL_DB")

    english_pattern = "|".join(ENGLISH_COUNTRIES)
    
    sql = f"""
        SELECT DISTINCT
            p.project_id,
            p.campaign_id,
            p.locations,
            p.creation_date
        FROM trc.geo_edge_projects p
        WHERE CONCAT(',', REPLACE(COALESCE(p.locations, ''), ' ', ''), ',') 
              REGEXP ',({english_pattern}),'
    """

    try:
        connection = pymysql.connect(
            host=host, port=port, user=user, password=password, database=database,
            cursorclass=pymysql.cursors.DictCursor,
        )
    except MySQLError as exc:
        print(f"❌ MySQL connection failed: {exc}")
        return {}

    try:
        with connection.cursor() as cursor:
            cursor.execute(sql)
            campaigns = {}
            for row in cursor.fetchall():
                campaign_id = str(row["campaign_id"])
                campaigns[campaign_id] = {
                    "project_id": row["project_id"],
                    "campaign_id": campaign_id,
                    "locations": row["locations"],
                }
            return campaigns
    finally:
        connection.close()


def fetch_lp_alerts_last_24h() -> List[Dict[str, Any]]:
    """Fetch Landing Page alerts from last 24 hours"""
    try:
        client = GeoEdgeClient()
    except Exception as e:
        print(f"❌ Failed to initialize GeoEdge client: {e}")
        return []

    now = datetime.utcnow()
    start_24h = now - timedelta(hours=24)

    min_datetime = start_24h.strftime("%Y-%m-%d %H:%M:%S")
    max_datetime = now.strftime("%Y-%m-%d %H:%M:%S")

    print(f"📅 Fetching alerts from {min_datetime} to {max_datetime}")

    lp_alerts = []
    count = 0
    
    try:
        for alert in client.iter_alerts_history(
            min_datetime=min_datetime,
            max_datetime=max_datetime,
            page_limit=5000,
            max_pages=100
        ):
            count += 1
            alert_name = alert.get("alert_name", "").lower()
            
            if "lp" in alert_name or "landing" in alert_name:
                lp_alerts.append(alert)
        
        print(f"📊 Scanned {count} alerts, found {len(lp_alerts)} LP alerts")
    except Exception as e:
        print(f"❌ Error fetching alerts: {e}")
        return []

    return lp_alerts


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


def match_alerts_to_english_campaigns(
    lp_alerts: List[Dict[str, Any]],
    english_campaigns: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Match LP alerts to English-targeting campaigns by extracting campaign_id from project_name"""
    matched_alerts = []
    
    for alert in lp_alerts:
        project_name_raw = alert.get("project_name", {})
        if isinstance(project_name_raw, dict) and project_name_raw:
            project_name = list(project_name_raw.values())[0]
        else:
            project_name = str(project_name_raw) if project_name_raw else ""
        
        # Extract campaign ID from project name
        campaign_id = extract_campaign_id_from_project_name(project_name)
        
        # Check if this campaign targets English countries
        if campaign_id in english_campaigns:
            matched_alerts.append({
                **alert,
                "matched_campaign_id": campaign_id,
            })
    
    return matched_alerts


def fetch_account_ids_for_campaigns(campaign_ids: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    """Fetch advertiser_id (account ID) from landing pages for matched campaigns"""
    if not campaign_ids:
        return {}

    host = _env_or_fail("MYSQL_HOST")
    port = int(os.getenv("MYSQL_PORT", "3306"))
    user = _env_or_fail("MYSQL_USER")
    password = _env_or_fail("MYSQL_PASSWORD")
    database = _env_or_fail("MYSQL_DB")

    unique_campaigns = list(set(campaign_ids))
    placeholders = ", ".join(["%s"] * len(unique_campaigns))
    sql = f"""
        SELECT DISTINCT
            lp.campaign_id,
            lp.advertiser_id,
            p.locations
        FROM trc.geo_edge_landing_pages lp
        JOIN trc.geo_edge_projects p ON p.campaign_id = lp.campaign_id
        WHERE lp.campaign_id IN ({placeholders})
    """

    try:
        connection = pymysql.connect(
            host=host, port=port, user=user, password=password, database=database,
            cursorclass=pymysql.cursors.DictCursor,
        )
    except MySQLError as exc:
        print(f"❌ MySQL connection failed: {exc}")
        return {}

    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, tuple(unique_campaigns))
            results = {}
            for row in cursor.fetchall():
                campaign_id = str(row["campaign_id"])
                if campaign_id not in results:
                    results[campaign_id] = []
                results[campaign_id].append({
                    "advertiser_id": str(row["advertiser_id"]),
                    "campaign_id": campaign_id,
                    "locations": row["locations"],
                })
            return results
    finally:
        connection.close()


def fetch_account_countries(account_ids: List[str]) -> Dict[str, str]:
    """Fetch account country codes from trc.publishers"""
    if not account_ids:
        return {}

    host = _env_or_fail("MYSQL_HOST")
    port = int(os.getenv("MYSQL_PORT", "3306"))
    user = _env_or_fail("MYSQL_USER")
    password = _env_or_fail("MYSQL_PASSWORD")
    database = _env_or_fail("MYSQL_DB")

    unique_ids = list(set(account_ids))
    placeholders = ", ".join(["%s"] * len(unique_ids))
    sql = f"SELECT id, country FROM trc.publishers WHERE id IN ({placeholders})"

    try:
        connection = pymysql.connect(
            host=host, port=port, user=user, password=password, database=database,
            cursorclass=pymysql.cursors.Cursor,
        )
    except MySQLError as exc:
        print(f"❌ MySQL connection failed: {exc}")
        return {}

    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, tuple(unique_ids))
            return {str(acc_id): country for acc_id, country in cursor.fetchall()}
    finally:
        connection.close()


def main():
    print("🚀 LATAM/Greater China LP Alerts Report (24h)")
    print("=" * 80)

    # Step 1: Fetch campaigns targeting English countries
    print("\n1️⃣ Fetching campaigns targeting English countries...")
    english_campaigns = fetch_english_targeting_campaigns()
    if not english_campaigns:
        print("❌ No campaigns found")
        return 1
    print(f"✅ Found {len(english_campaigns)} campaigns")

    # Step 2: Fetch LP alerts
    print("\n2️⃣ Fetching Landing Page alerts (last 24h)...")
    lp_alerts = fetch_lp_alerts_last_24h()
    if not lp_alerts:
        print("⚠️ No LP alerts found")
        return 0

    # Step 3: Match alerts to English-targeting campaigns
    print("\n3️⃣ Matching alerts to English campaigns...")
    matched_alerts = match_alerts_to_english_campaigns(lp_alerts, english_campaigns)
    if not matched_alerts:
        print("⚠️ No alerts matched to English campaigns")
        return 0
    print(f"✅ Found {len(matched_alerts)} matching alerts")

    # Step 4: Fetch account IDs
    print("\n4️⃣ Fetching account IDs from landing pages...")
    matched_campaign_ids = [alert["matched_campaign_id"] for alert in matched_alerts]
    campaign_to_accounts = fetch_account_ids_for_campaigns(matched_campaign_ids)
    if not campaign_to_accounts:
        print("⚠️ No accounts found")
        return 0

    # Collect all account IDs
    all_account_ids = []
    for campaign_accounts in campaign_to_accounts.values():
        for acc_info in campaign_accounts:
            all_account_ids.append(acc_info["advertiser_id"])

    # Step 5: Fetch account countries
    print("\n5️⃣ Fetching account countries...")
    account_countries = fetch_account_countries(all_account_ids)

    # Step 6: Filter for LATAM and Greater China
    print("\n6️⃣ Filtering for LATAM and Greater China accounts...")
    filtered_data = []
    for campaign_id, accounts in campaign_to_accounts.items():
        for acc_info in accounts:
            account_id = acc_info["advertiser_id"]
            country = account_countries.get(account_id, "")
            if country in TARGET_REGIONS:
                filtered_data.append({
                    "account_id": account_id,
                    "country": country,
                    "region": "LATAM" if country in LATAM_COUNTRIES else "Greater China",
                    "campaign_id": campaign_id,
                    "locations": acc_info["locations"],
                })

    if not filtered_data:
        print("⚠️ No LATAM/Greater China accounts found")
        return 0

    print(f"✅ Found {len(filtered_data)} matching records")

    # Step 7: Output to CSV
    print("\n7️⃣ Saving to CSV...")
    output_file = "/Users/gaurav.k/Desktop/geoedge-country-projects/latam_greater_china_lp_alerts_24h.csv"

    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Account ID", "Country", "Region", "Campaign ID", "Target Locations"])
        
        for row in sorted(filtered_data, key=lambda x: x["account_id"]):
            writer.writerow([
                row["account_id"],
                row["country"],
                row["region"],
                row["campaign_id"],
                row["locations"],
            ])

    print(f"✅ Saved to: {output_file}")
    latam_count = sum(1 for d in filtered_data if d["region"] == "LATAM")
    china_count = sum(1 for d in filtered_data if d["region"] == "Greater China")
    print(f"\n📊 Summary:")
    print(f"   - LATAM: {latam_count}")
    print(f"   - Greater China: {china_count}")
    print(f"   - Total: {len(filtered_data)}")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
