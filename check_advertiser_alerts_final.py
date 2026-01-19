#!/usr/bin/env python3
"""Check alerts for specific advertisers in the last 90 days using parallel processing - FIXED VERSION."""

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
import pandas as pd

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
            SELECT id, name, status
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
    
    # Debug: Check for specific alert types mentioned by user
    print("\n=== DEBUG: Checking for specific alert types ===")
    alert_types_found = {}
    target_accounts_in_alerts = set()
    
    for alert in alerts:
        alert_name = alert.get('alert_name', '').lower()
        trigger_metadata = alert.get('trigger_metadata', '').lower()
        
        # Check for specific alert types
        if any(keyword in alert_name or keyword in trigger_metadata for keyword in 
               ['deceptive', 'malicious domain', 'financial', 'cloaking']):
            alert_type_key = f"{alert_name}|{trigger_metadata}"
            if alert_type_key not in alert_types_found:
                alert_types_found[alert_type_key] = []
            alert_types_found[alert_type_key].append(alert)
        
        # Check if any target accounts appear anywhere in the alert data
        alert_str = str(alert).lower()
        for target_id in TARGET_ADVERTISER_IDS:
            if target_id in alert_str:
                target_accounts_in_alerts.add(target_id)
    
    print(f"Found {len(alert_types_found)} different types of suspicious alerts:")
    for alert_type, alert_list in alert_types_found.items():
        print(f"  - {alert_type}: {len(alert_list)} alerts")
    
    print(f"Target accounts found anywhere in alert data: {sorted(target_accounts_in_alerts)}")
    
    if not alerts:
        print("No alerts found in the specified time period")
        return

    # Step 2: Enhanced account ID extraction with debugging
    print("\n=== Step 2: Enhanced account ID extraction ===")
    
    # Method 1: Extract project IDs from alerts
    project_ids_in_alerts = extract_project_ids_from_alerts(alerts)
    print(f"Found {len(project_ids_in_alerts)} unique project IDs in alerts")
    
    # Method 2: Get account IDs from project IDs
    project_to_account_map = get_accounts_from_project_ids(list(project_ids_in_alerts))
    account_ids_from_projects = set(project_to_account_map.values())
    print(f"Found {len(account_ids_from_projects)} unique account IDs from projects")
    
    # Method 3: Extract account IDs directly from alerts
    direct_account_ids = extract_account_ids_from_alerts(alerts)
    print(f"Found {len(direct_account_ids)} account IDs directly from alerts")
    
    # Method 4: NEW - Look for target accounts in ALL alert fields
    accounts_from_all_fields = set()
    suspicious_alerts_by_account = defaultdict(list)
    
    print("\n=== DEBUG: Scanning ALL alert fields for target accounts ===")
    for alert in alerts:
        # Convert entire alert to string and search for target IDs
        alert_str = str(alert)
        
        for target_id in TARGET_ADVERTISER_IDS:
            if target_id in alert_str:
                accounts_from_all_fields.add(target_id)
                # Check if this is a suspicious alert type
                alert_name = alert.get('alert_name', '').lower()
                trigger_metadata = alert.get('trigger_metadata', '').lower()
                
                if any(keyword in alert_name or keyword in trigger_metadata for keyword in 
                       ['deceptive', 'malicious', 'financial', 'cloaking', 'security']):
                    suspicious_alerts_by_account[target_id].append({
                        'alert': alert,
                        'found_method': 'string_search'
                    })
    
    print(f"Target accounts found via string search: {sorted(accounts_from_all_fields)}")
    
    # Combine all methods
    all_account_ids = account_ids_from_projects.union(direct_account_ids).union(accounts_from_all_fields)
    print(f"Total unique account IDs: {len(all_account_ids)}")
    
    # Step 3: Find matches with target advertisers
    print("\n=== Step 3: Finding matches with target advertisers ===")
    target_set = set(TARGET_ADVERTISER_IDS)
    matching_accounts = all_account_ids.intersection(target_set)
    
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
                      f"(Status: {details.get('status', 'Unknown')})")
            else:
                print(f"  - Account {account_id}: No details found in database")
    
    # Step 5: ENHANCED Alert analysis with multiple methods
    print("\n=== Step 5: Enhanced alert analysis ===")
    alert_counts = defaultdict(int)
    alert_details = defaultdict(list)
    
    # Method 1: Traditional project mapping
    for alert in alerts:
        if 'project_name' in alert and isinstance(alert['project_name'], dict):
            for project_id in alert['project_name'].keys():
                if project_id in project_to_account_map:
                    account_id = project_to_account_map[project_id]
                    if account_id in target_set:
                        alert_counts[account_id] += 1
                        alert_info = {
                            'alert_id': alert.get('alert_id', 'Unknown'),
                            'history_id': alert.get('history_id', 'Unknown'),
                            'trigger_type_id': alert.get('trigger_type_id', 'Unknown'),
                            'trigger_metadata': alert.get('trigger_metadata', ''),
                            'alert_name': alert.get('alert_name', 'Unknown'),
                            'event_datetime': alert.get('event_datetime', 'Unknown'),
                            'alert_details_url': alert.get('alert_details_url', 'No URL available'),
                            'project_id': project_id,
                            'project_name': alert['project_name'].get(project_id, 'Unknown'),
                            'location': alert.get('location', {}),
                            'ad_id': alert.get('ad_id', 'Unknown'),
                            'detection_method': 'project_mapping'
                        }
                        alert_details[account_id].append(alert_info)
    
    # Method 2: Enhanced string search - scan ALL alerts for target accounts
    print("    Scanning all alerts for target account IDs...")
    target_set = set(TARGET_ADVERTISER_IDS)
    
    for alert in alerts:
        # Convert entire alert to JSON string for comprehensive search
        alert_json_str = str(alert)
        
        # Check if any target account ID appears ANYWHERE in the alert
        for target_id in target_set:
            if target_id in alert_json_str:
                # Found target account - extract the alert information
                if target_id not in alert_counts or alert.get('alert_id') not in [a['alert_id'] for a in alert_details.get(target_id, [])]:
                    alert_counts[target_id] += 1
                    
                    # Try to find project info if available
                    project_info = "Found via comprehensive search"
                    project_id = "comprehensive_search"
                    
                    if 'project_name' in alert and isinstance(alert['project_name'], dict):
                        project_names = list(alert['project_name'].values())
                        if project_names:
                            project_info = project_names[0]
                            project_id = list(alert['project_name'].keys())[0]
                    
                    alert_info = {
                        'alert_id': alert.get('alert_id', 'Unknown'),
                        'history_id': alert.get('history_id', 'Unknown'),
                        'trigger_type_id': alert.get('trigger_type_id', 'Unknown'),
                        'trigger_metadata': alert.get('trigger_metadata', ''),
                        'alert_name': alert.get('alert_name', 'Unknown'),
                        'event_datetime': alert.get('event_datetime', 'Unknown'),
                        'alert_details_url': alert.get('alert_details_url', 'No URL available'),
                        'project_id': project_id,
                        'project_name': project_info,
                        'location': alert.get('location', {}),
                        'ad_id': alert.get('ad_id', 'Unknown'),
                        'detection_method': 'comprehensive_search'
                    }
                    
                    if target_id not in alert_details:
                        alert_details[target_id] = []
                    alert_details[target_id].append(alert_info)
                    
                    print(f"    🎯 Found {target_id} in alert: {alert.get('alert_name', 'Unknown')} | {alert.get('trigger_metadata', 'Unknown')} | {alert.get('event_datetime', 'Unknown')}")
    
    # Update matching_accounts to include any newly found accounts
    matching_accounts = matching_accounts.union(set(alert_counts.keys()))
    print(f"    Total unique accounts found with alerts: {len(matching_accounts)}")
    
    if alert_counts:
        print("Alert counts and details:")
        
        # Get updated account details for any newly found accounts
        if matching_accounts:
            account_details = get_account_mapping_from_db(list(matching_accounts))
        
        for account_id in sorted(alert_counts.keys()):
            account_name = "Unknown"
            if account_id in account_details:
                account_name = account_details[account_id].get('name', 'Unknown')
            
            print(f"\n🚨 ACCOUNT {account_id} ({account_name}): {alert_counts[account_id]} alerts")
            
            for i, alert_info in enumerate(alert_details[account_id], 1):
                print(f"   Alert #{i} (Method: {alert_info.get('detection_method', 'unknown')}):")
                print(f"     • Alert ID: {alert_info['alert_id']}")
                print(f"     • Alert Name: {alert_info['alert_name']}")
                print(f"     • Trigger Type ID: {alert_info['trigger_type_id']}")
                print(f"     • Trigger Metadata: {alert_info['trigger_metadata']}")
                print(f"     • Event DateTime: {alert_info['event_datetime']}")
                print(f"     • Project: {alert_info['project_name']} ({alert_info['project_id']})")
                print(f"     • Location: {alert_info['location']}")
                print(f"     • Ad ID: {alert_info['ad_id']}")
                print(f"     • Alert Details URL: {alert_info['alert_details_url']}")
                print()
        
        total_alerts = sum(alert_counts.values())
        print(f"Total alerts for target advertisers: {total_alerts}")
    else:
        print("No alerts found for target advertisers")
    
    # Step 6: List advertisers with no alerts
    print("\n=== Step 6: Target advertisers with no alerts ===")
    no_alerts = target_set - set(alert_counts.keys())
    if no_alerts:
        print(f"Found {len(no_alerts)} target advertisers with NO alerts:")
        for account_id in sorted(no_alerts):
            print(f"  - Account {account_id}: No alerts found")
    else:
        print("All target advertisers have alerts!")
    
    print(f"\n=== FINAL SUMMARY ===")
    print(f"Total alerts fetched: {len(alerts):,}")
    print(f"Unique accounts with alerts: {len(all_account_ids):,}")
    print(f"Target advertisers with alerts: {len(alert_counts)}")
    print(f"Target advertisers without alerts: {len(no_alerts)}")
    
    if alert_counts:
        print(f"\n🚨 ADVERTISERS WITH ALERTS FOUND:")
        excel_data = []
        
        for account_id in sorted(alert_counts.keys()):
            count = alert_counts.get(account_id, 0)
            account_name = "Unknown"
            if account_id in account_details:
                account_name = account_details[account_id].get('name', 'Unknown')
            print(f"   • Account {account_id} ({account_name}): {count} alerts")
            
            # Add alert details to Excel data
            for alert_info in alert_details.get(account_id, []):
                location_str = ", ".join([f"{k}: {v}" for k, v in alert_info['location'].items()])
                excel_data.append({
                    'Account ID': account_id,
                    'Account Name': account_name,
                    'Alert ID': alert_info['alert_id'],
                    'Alert Name': alert_info['alert_name'],
                    'Trigger Type ID': alert_info['trigger_type_id'],
                    'Trigger Metadata': alert_info['trigger_metadata'],
                    'Event DateTime': alert_info['event_datetime'],
                    'Project Name': alert_info['project_name'],
                    'Project ID': alert_info['project_id'],
                    'Location': location_str,
                    'Ad ID': alert_info['ad_id'],
                    'Alert Details URL': alert_info['alert_details_url'],
                    'Detection Method': alert_info.get('detection_method', 'unknown')
                })
        
        # Create Excel file
        if excel_data:
            df = pd.DataFrame(excel_data)
            excel_filename = f"advertiser_alerts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            
            # Create Excel writer with xlsxwriter engine for better formatting
            with pd.ExcelWriter(excel_filename, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Alert Details', index=False)
                
                # Get the workbook and worksheet
                workbook = writer.book
                worksheet = writer.sheets['Alert Details']
                
                # Auto-adjust column widths
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 100)  # Cap at 100 characters
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            print(f"\n📊 Excel file created: {excel_filename}")
            print(f"   Contains {len(excel_data)} alert records with clickable links")
        
        return excel_filename if excel_data else None


if __name__ == "__main__":
    try:
        analyze_alerts_for_advertisers()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)