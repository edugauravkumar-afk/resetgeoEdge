#!/usr/bin/env python3
"""Check alerts for specific advertisers in the last 90 days using parallel processing."""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Set, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from collections import defaultdict
from dotenv import load_dotenv
import pymysql
from pymysql import MySQLError
import requests

load_dotenv()

# Target advertiser IDs to check
TARGET_ADVERTISER_IDS = [
    "1790942", "1906171", "1413880", "1627055", "1790070", "1892241", "1830732", "1180902",
    "1819766", "1800364", "1795625", "1893748", "1798665", "1895958", "1675720", "1929304",
    "1923113", "1496584", "1929287", "1425690", "1927701", "1279600", "1905236", "1793447",
    "1817514", "1443633", "1885711", "1895960", "1903778", "1933684", "1798931", "1929299",
    "1858379", "1906170", "1883417", "1920194"
]

# Thread-safe collections
alerts_lock = threading.Lock()
all_alerts = []

def _env_or_fail(key: str) -> str:
    value = os.getenv(key, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return value


def fetch_alerts_chunk_direct_api(start_date: datetime, end_date: datetime, 
                                 thread_id: int) -> List[Dict[str, Any]]:
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
        limit = 5000  # Reduced limit to avoid timeouts
        
        while True:
            params = {
                "min_datetime": start_str,
                "max_datetime": end_str,
                "offset": offset,
                "limit": limit,
                "full_raw": 1  # Get all alerts, not just unique ones
            }
            
            print(f"Thread {thread_id}: Requesting offset {offset}, limit {limit}")
            
            # Create session with retries
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
                print(f"Thread {thread_id}: Unexpected response format")
                break
            
            if not batch_alerts:
                print(f"Thread {thread_id}: No more alerts found")
                break
            
            alerts.extend(batch_alerts)
            print(f"Thread {thread_id}: Retrieved {len(batch_alerts)} alerts in this batch (total: {len(alerts)})")
            
            # Check if there are more pages
            if "next_page" not in data or not data["next_page"]:
                break
                
            offset += len(batch_alerts)
            
            # Safety check to avoid infinite loops
            if offset > 100000:  # 100k alerts max per chunk
                print(f"Thread {thread_id}: Reached safety limit of 100k alerts")
                break
            
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


def fetch_all_alerts_parallel(days: int = 90, num_threads: int = 6) -> List[Dict[str, Any]]:
    """Fetch all alerts in parallel using multiple threads."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    print(f"Fetching alerts from {start_date.date()} to {end_date.date()} using {num_threads} threads")
    
    # Split the time range into smaller chunks (7 days each) for parallel processing
    chunk_days = 7  # Weekly chunks to avoid timeouts
    date_ranges = []
    current_start = start_date
    thread_id = 0
    
    while current_start < end_date:
        chunk_end = min(current_start + timedelta(days=chunk_days), end_date)
        date_ranges.append((current_start, chunk_end, thread_id))
        current_start = chunk_end
        thread_id += 1
    
    print(f"Created {len(date_ranges)} time chunks of ~{chunk_days} days each")
    
    # Use ThreadPoolExecutor for parallel processing
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        # Submit all tasks
        futures = [
            executor.submit(fetch_alerts_chunk_direct_api, start, end, tid)
            for start, end, tid in date_ranges
        ]
        
        # Wait for all tasks to complete
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"Thread failed with error: {e}")
    
    print(f"Total alerts retrieved: {len(all_alerts)}")
    return all_alerts


def get_account_mapping_from_db(account_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """Get account details from database."""
    if not account_ids:
        return {}
    
    try:
        host = _env_or_fail("MYSQL_HOST")
        port = int(os.getenv("MYSQL_PORT", "3306"))
        user = _env_or_fail("MYSQL_USER")
        password = _env_or_fail("MYSQL_PASSWORD")
        database = _env_or_fail("MYSQL_DB")
        
        connection = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            cursorclass=pymysql.cursors.DictCursor,
        )
        
        placeholders = ", ".join(["%s"] * len(account_ids))
        sql = f"""
            SELECT id, name, status, created_at
            FROM trc.publishers
            WHERE id IN ({placeholders})
        """
        
        with connection.cursor() as cursor:
            cursor.execute(sql, account_ids)
            results = cursor.fetchall()
            
        connection.close()
        
        # Convert to dict with account_id as key
        return {str(row['id']): row for row in results}
        
    except MySQLError as e:
        print(f"Database error: {e}")
        return {}


def extract_account_ids_from_alerts(alerts: List[Dict[str, Any]]) -> Set[str]:
    """Extract unique account IDs from alerts."""
    account_ids = set()
    
    for alert in alerts:
        # Try different possible field names for account ID based on API docs
        account_id = None
        
        # Check common field names that might contain account information
        for field in ['account_id', 'publisher_id', 'syndicator_id', 'advertiser_id']:
            if field in alert and alert[field]:
                account_id = str(alert[field])
                break
        
        # If not found in direct fields, check nested objects
        if not account_id:
            # Check project_name structure - it contains project_id -> project_name mapping
            if 'project_name' in alert and isinstance(alert['project_name'], dict):
                # The project_name field contains project IDs as keys
                for project_id in alert['project_name'].keys():
                    # We need to get the account from the project_id via database
                    # For now, skip this approach as it's complex
                    pass
        
        # Try to extract from other possible locations
        if not account_id and 'alert_details_url' in alert:
            # Sometimes account info is in the URL structure
            # Example: https://site.geoedge.com/analyticsv2/ad/1021141477/...
            url = alert['alert_details_url']
            url_parts = url.split('/')
            for i, part in enumerate(url_parts):
                if part == 'ad' and i + 1 < len(url_parts):
                    potential_id = url_parts[i + 1]
                    if potential_id.isdigit():
                        account_id = potential_id
                        break
        
        if account_id and account_id.isdigit():
            account_ids.add(account_id)
    
    return account_ids


def extract_project_ids_from_alerts(alerts: List[Dict[str, Any]]) -> Set[str]:
    """Extract unique project IDs from alerts to later map to accounts."""
    project_ids = set()
    
    for alert in alerts:
        # Check project_name field which contains project_id -> project_name mapping
        if 'project_name' in alert and isinstance(alert['project_name'], dict):
            for project_id in alert['project_name'].keys():
                if project_id:
                    project_ids.add(project_id)
    
    return project_ids


def get_accounts_from_project_ids(project_ids: List[str]) -> Dict[str, str]:
    """Get account IDs from project IDs using database."""
    if not project_ids:
        return {}
    
    try:
        host = _env_or_fail("MYSQL_HOST")
        port = int(os.getenv("MYSQL_PORT", "3306"))
        user = _env_or_fail("MYSQL_USER")
        password = _env_or_fail("MYSQL_PASSWORD")
        database = _env_or_fail("MYSQL_DB")
        
        connection = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            cursorclass=pymysql.cursors.DictCursor,
        )
        
        placeholders = ", ".join(["%s"] * len(project_ids))
        sql = f"""
            SELECT p.project_id, c.syndicator_id
            FROM trc.geo_edge_projects p
            JOIN trc.sp_campaigns c ON p.campaign_id = c.id
            WHERE p.project_id IN ({placeholders})
        """
        
        with connection.cursor() as cursor:
            cursor.execute(sql, project_ids)
            results = cursor.fetchall()
            
        connection.close()
        
        # Convert to dict with project_id -> account_id mapping
        return {row['project_id']: str(row['syndicator_id']) for row in results}
        
    except MySQLError as e:
        print(f"Database error: {e}")
        return {}


def analyze_alerts_for_advertisers():
    """Main function to analyze alerts for target advertisers."""
    print(f"Checking alerts for {len(TARGET_ADVERTISER_IDS)} advertiser IDs in the last 90 days")
    print(f"Target advertisers: {', '.join(TARGET_ADVERTISER_IDS[:5])}..." + 
          (f" (and {len(TARGET_ADVERTISER_IDS)-5} more)" if len(TARGET_ADVERTISER_IDS) > 5 else ""))
    
    # Step 1: Fetch all alerts in parallel
    print("\n=== Step 1: Fetching alerts in parallel ===")
    alerts = fetch_all_alerts_parallel(days=90, num_threads=4)  # Reduced threads to avoid overloading API
    
    if not alerts:
        print("No alerts found in the specified time period")
        return
    
    # Step 2: Extract project IDs from alerts
    print("\n=== Step 2: Extracting project IDs from alerts ===")
    project_ids_in_alerts = extract_project_ids_from_alerts(alerts)
    print(f"Found {len(project_ids_in_alerts)} unique project IDs in alerts")
    
    # Step 3: Get account IDs from project IDs
    print("\n=== Step 3: Getting account IDs from project IDs ===")
    project_to_account_map = get_accounts_from_project_ids(list(project_ids_in_alerts))
    account_ids_in_alerts = set(project_to_account_map.values())
    print(f"Found {len(account_ids_in_alerts)} unique account IDs from projects")
    
    # Step 4: Also try to extract account IDs directly from alerts
    print("\n=== Step 4: Extracting account IDs directly from alerts ===")
    direct_account_ids = extract_account_ids_from_alerts(alerts)
    print(f"Found {len(direct_account_ids)} account IDs directly from alerts")
    
    # Combine both approaches
    all_account_ids = account_ids_in_alerts.union(direct_account_ids)
    print(f"Total unique account IDs: {len(all_account_ids)}")
    
    # Step 5: Find matches with target advertisers
    print("\n=== Step 5: Finding matches with target advertisers ===")
    target_set = set(TARGET_ADVERTISER_IDS)
    matching_accounts = all_account_ids.intersection(target_set)
    
    print(f"Found {len(matching_accounts)} target advertisers with alerts:")
    if matching_accounts:
        print("Matching advertiser IDs:", sorted(matching_accounts))
    else:
        print("No target advertisers found with alerts in the last 90 days")
    
    # Step 6: Get detailed info for matching accounts
    if matching_accounts:
        print("\n=== Step 6: Getting detailed account information ===")
        account_details = get_account_mapping_from_db(list(matching_accounts))
        
        print("\nDetailed information for matching accounts:")
        for account_id in sorted(matching_accounts):
            if account_id in account_details:
                details = account_details[account_id]
                print(f"  - Account {account_id}: {details.get('name', 'Unknown')} "
                      f"(Status: {details.get('status', 'Unknown')}, "
                      f"Created: {details.get('created_at', 'Unknown')})")
            else:
                print(f"  - Account {account_id}: No details found in database")
    
    # Step 7: Count alerts per matching advertiser
    print("\n=== Step 7: Alert counts per matching advertiser ===")
    alert_counts = defaultdict(int)
    
    # Count alerts by mapping projects back to accounts
    for alert in alerts:
        if 'project_name' in alert and isinstance(alert['project_name'], dict):
            for project_id in alert['project_name'].keys():
                if project_id in project_to_account_map:
                    account_id = project_to_account_map[project_id]
                    if account_id in matching_accounts:
                        alert_counts[account_id] += 1
    
    if alert_counts:
        print("Alert counts:")
        for account_id in sorted(alert_counts.keys()):
            print(f"  - Account {account_id}: {alert_counts[account_id]} alerts")
        
        total_alerts = sum(alert_counts.values())
        print(f"Total alerts for target advertisers: {total_alerts}")
    
    # Step 8: List advertisers with no alerts
    print("\n=== Step 8: Target advertisers with no alerts ===")
    no_alerts = target_set - matching_accounts
    if no_alerts:
        print(f"Found {len(no_alerts)} target advertisers with NO alerts:")
        for account_id in sorted(no_alerts):
            print(f"  - Account {account_id}: No alerts found")
    else:
        print("All target advertisers have alerts!")
    
    print(f"\n=== Summary ===")
    print(f"Total alerts fetched: {len(alerts)}")
    print(f"Unique accounts with alerts: {len(all_account_ids)}")
    print(f"Target advertisers with alerts: {len(matching_accounts)}")
    print(f"Target advertisers without alerts: {len(no_alerts)}")


if __name__ == "__main__":
    try:
        analyze_alerts_for_advertisers()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def fetch_all_alerts_parallel(days: int = 90, num_threads: int = 10) -> List[Dict[str, Any]]:
    """Fetch all alerts in parallel using multiple threads."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    print(f"Fetching alerts from {start_date.date()} to {end_date.date()} using {num_threads} threads")
    
    # Split the time range into chunks for parallel processing
    total_days = (end_date - start_date).days
    days_per_chunk = max(1, total_days // num_threads)
    
    # Create date ranges for each thread
    date_ranges = []
    current_start = start_date
    
    for i in range(num_threads):
        chunk_end = current_start + timedelta(days=days_per_chunk)
        if i == num_threads - 1:  # Last chunk gets remaining days
            chunk_end = end_date
            
        date_ranges.append((current_start, chunk_end, i))
        current_start = chunk_end
        
        if current_start >= end_date:
            break
    
    # Initialize GeoEdge client
    client = GeoEdgeClient()
    
    # Use ThreadPoolExecutor for parallel processing
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        # Submit all tasks
        futures = [
            executor.submit(fetch_alerts_chunk, client, start, end, thread_id)
            for start, end, thread_id in date_ranges
        ]
        
        # Wait for all tasks to complete
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"Thread failed with error: {e}")
    
    print(f"Total alerts retrieved: {len(all_alerts)}")
    return all_alerts


def get_account_mapping_from_db(account_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """Get account details from database."""
    if not account_ids:
        return {}
    
    try:
        host = _env_or_fail("MYSQL_HOST")
        port = int(os.getenv("MYSQL_PORT", "3306"))
        user = _env_or_fail("MYSQL_USER")
        password = _env_or_fail("MYSQL_PASSWORD")
        database = _env_or_fail("MYSQL_DB")
        
        connection = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            cursorclass=pymysql.cursors.DictCursor,
        )
        
        placeholders = ", ".join(["%s"] * len(account_ids))
        sql = f"""
            SELECT id, name, status, created_at
            FROM trc.publishers
            WHERE id IN ({placeholders})
        """
        
        with connection.cursor() as cursor:
            cursor.execute(sql, account_ids)
            results = cursor.fetchall()
            
        connection.close()
        
        # Convert to dict with account_id as key
        return {str(row['id']): row for row in results}
        
    except MySQLError as e:
        print(f"Database error: {e}")
        return {}


def extract_account_ids_from_alerts(alerts: List[Dict[str, Any]]) -> Set[str]:
    """Extract unique account IDs from alerts."""
    account_ids = set()
    
    for alert in alerts:
        # Try different possible field names for account ID
        account_id = None
        
        # Check common field names
        for field in ['account_id', 'publisher_id', 'syndicator_id', 'advertiser_id']:
            if field in alert and alert[field]:
                account_id = str(alert[field])
                break
        
        # If not found in direct fields, check nested objects
        if not account_id:
            if 'publisher' in alert and isinstance(alert['publisher'], dict):
                account_id = str(alert['publisher'].get('id', ''))
            elif 'syndicator' in alert and isinstance(alert['syndicator'], dict):
                account_id = str(alert['syndicator'].get('id', ''))
        
        if account_id and account_id.isdigit():
            account_ids.add(account_id)
    
    return account_ids


def analyze_alerts_for_advertisers():
    """Main function to analyze alerts for target advertisers."""
    print(f"Checking alerts for {len(TARGET_ADVERTISER_IDS)} advertiser IDs in the last 90 days")
    print(f"Target advertisers: {', '.join(TARGET_ADVERTISER_IDS[:5])}..." + 
          (f" (and {len(TARGET_ADVERTISER_IDS)-5} more)" if len(TARGET_ADVERTISER_IDS) > 5 else ""))
    
    # Step 1: Fetch all alerts in parallel
    print("\n=== Step 1: Fetching alerts in parallel ===")
    alerts = fetch_all_alerts_parallel(days=90, num_threads=12)
    
    if not alerts:
        print("No alerts found in the specified time period")
        return
    
    # Step 2: Extract account IDs from alerts
    print("\n=== Step 2: Extracting account IDs from alerts ===")
    account_ids_in_alerts = extract_account_ids_from_alerts(alerts)
    print(f"Found {len(account_ids_in_alerts)} unique account IDs in alerts")
    
    # Step 3: Find matches with target advertisers
    print("\n=== Step 3: Finding matches with target advertisers ===")
    target_set = set(TARGET_ADVERTISER_IDS)
    matching_accounts = account_ids_in_alerts.intersection(target_set)
    
    print(f"Found {len(matching_accounts)} target advertisers with alerts:")
    if matching_accounts:
        print("Matching advertiser IDs:", sorted(matching_accounts))
    else:
        print("No target advertisers found with alerts in the last 90 days")
    
    # Step 4: Get detailed info for matching accounts
    if matching_accounts:
        print("\n=== Step 4: Getting detailed account information ===")
        account_details = get_account_mapping_from_db(list(matching_accounts))
        
        print("\nDetailed information for matching accounts:")
        for account_id in sorted(matching_accounts):
            if account_id in account_details:
                details = account_details[account_id]
                print(f"  - Account {account_id}: {details.get('name', 'Unknown')} "
                      f"(Status: {details.get('status', 'Unknown')}, "
                      f"Created: {details.get('created_at', 'Unknown')})")
            else:
                print(f"  - Account {account_id}: No details found in database")
    
    # Step 5: Count alerts per matching advertiser
    print("\n=== Step 5: Alert counts per matching advertiser ===")
    alert_counts = defaultdict(int)
    
    for alert in alerts:
        account_id = None
        for field in ['account_id', 'publisher_id', 'syndicator_id', 'advertiser_id']:
            if field in alert and alert[field]:
                account_id = str(alert[field])
                break
        
        if not account_id:
            if 'publisher' in alert and isinstance(alert['publisher'], dict):
                account_id = str(alert['publisher'].get('id', ''))
            elif 'syndicator' in alert and isinstance(alert['syndicator'], dict):
                account_id = str(alert['syndicator'].get('id', ''))
        
        if account_id in matching_accounts:
            alert_counts[account_id] += 1
    
    if alert_counts:
        print("Alert counts:")
        for account_id in sorted(alert_counts.keys()):
            print(f"  - Account {account_id}: {alert_counts[account_id]} alerts")
        
        total_alerts = sum(alert_counts.values())
        print(f"Total alerts for target advertisers: {total_alerts}")
    
    # Step 6: List advertisers with no alerts
    print("\n=== Step 6: Target advertisers with no alerts ===")
    no_alerts = target_set - matching_accounts
    if no_alerts:
        print(f"Found {len(no_alerts)} target advertisers with NO alerts:")
        for account_id in sorted(no_alerts):
            print(f"  - Account {account_id}: No alerts found")
    else:
        print("All target advertisers have alerts!")
    
    print(f"\n=== Summary ===")
    print(f"Total alerts fetched: {len(alerts)}")
    print(f"Unique accounts with alerts: {len(account_ids_in_alerts)}")
    print(f"Target advertisers with alerts: {len(matching_accounts)}")
    print(f"Target advertisers without alerts: {len(no_alerts)}")


if __name__ == "__main__":
    try:
        analyze_alerts_for_advertisers()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)