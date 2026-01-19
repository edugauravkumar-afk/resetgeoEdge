# pyright: reportGeneralTypeIssues=false

import os
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import pandas as pd
import pymysql
import vertica_python
import streamlit as st
from dotenv import load_dotenv

from geoedge_projects.client import GeoEdgeClient

load_dotenv()


class AlertsAnalyzer:
    """GeoEdge Alerts Analysis Dashboard"""

    def __init__(self):
        self.client: Optional[GeoEdgeClient] = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize GeoEdge client"""
        try:
            self.client = GeoEdgeClient()
        except Exception as e:
            st.error(f"Failed to initialize GeoEdge client: {e}")
            self.client = None

    def fetch_alerts_history(
        self,
        min_datetime: str,
        max_datetime: Optional[str] = None,
        project_id: Optional[str] = None,
        alert_id: Optional[str] = None,
        trigger_type_id: Optional[str] = None,
        location_ids: Optional[List[str]] = None,
        full_raw: bool = False,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Fetch alerts history from GeoEdge API
        
        Args:
            min_datetime: Minimum datetime (YYYY-MM-DD HH:MM:SS)
            max_datetime: Maximum datetime (YYYY-MM-DD HH:MM:SS)
            project_id: Single project ID filter
            alert_id: Single alert ID filter
            trigger_type_id: Single trigger type ID filter
            location_ids: List of location IDs
            full_raw: Return all alerts including duplicates
            limit: Maximum number of records per request
        
        Returns:
            List of alert history records
        """
        if not self.client:
            return []

        all_alerts = []
        
        try:
            # Convert location_ids list to comma-separated string if provided
            location_id_str = ','.join(location_ids) if location_ids else None
            
            # Use the existing client iterator method
            for alert in self.client.iter_alerts_history(
                project_id=project_id,
                alert_id=alert_id,
                trigger_type_id=trigger_type_id,
                min_datetime=min_datetime,
                max_datetime=max_datetime,
                location_id=location_id_str,
                full_raw=1 if full_raw else 0,
                page_limit=min(limit, 10000),  # API max is 10,000
                max_pages=50  # Safety limit to prevent infinite loops
            ):
                all_alerts.append(alert)
                
                # Safety check to prevent memory issues
                if len(all_alerts) >= 50000:  # Reasonable limit
                    st.warning("Reached maximum alert limit (50,000). Consider narrowing your search criteria.")
                    break

        except Exception as e:
            st.error(f"Error fetching alerts history: {e}")
            return []

        return all_alerts

    def fetch_project_details(self, project_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Fetch project details for given project IDs"""
        if not self.client or not project_ids:
            return {}

        project_details = {}
        
        with st.spinner(f"Fetching details for {len(project_ids)} projects..."):
            for i, project_id in enumerate(project_ids):
                try:
                    project_data = self.client.get_project(project_id)
                    if project_data:
                        project_details[project_id] = project_data
                except Exception as e:
                    # Silently continue on error - don't spam the user with warnings
                    project_details[project_id] = {'error': str(e)}

        return project_details

    def fetch_trigger_types(self) -> Dict[str, str]:
        """Fetch available trigger types"""
        if not self.client:
            return {}

        try:
            trigger_mapping = self.client.list_alert_trigger_types()
            # Convert to simple id -> description mapping
            return {
                trigger_id: data.get('description', f'Unknown ({trigger_id})')
                for trigger_id, data in trigger_mapping.items()
            }
        except Exception as e:
            st.warning(f"Could not fetch trigger types: {e}")

        return {}

    def fetch_campaign_accounts_from_db(self, campaign_ids: List[str]) -> Dict[str, str]:
        """Fetch campaign to account mapping from database (tries MySQL first, then Vertica)"""
        if not campaign_ids:
            return {}

        unique_ids = sorted({int(str(cid)) for cid in campaign_ids if str(cid).strip().isdigit()})
        if not unique_ids:
            return {}

        results: Dict[str, str] = {}
        
        # Try MySQL first
        try:
            host = os.getenv("MYSQL_HOST") or ""
            port = int(os.getenv("MYSQL_PORT", "3306"))
            user = os.getenv("MYSQL_USER") or ""
            password = os.getenv("MYSQL_PASSWORD") or ""
            db = os.getenv("MYSQL_DB") or ""

            if host and user and password and db:
                connection = pymysql.connect(
                    host=host,
                    port=port,
                    user=user,
                    password=password,
                    database=db,
                    charset="utf8mb4",
                    cursorclass=pymysql.cursors.Cursor,
                    autocommit=True,
                    read_timeout=60,
                    write_timeout=60,
                )
                
                with connection.cursor() as cursor:
                    # Process in chunks to avoid query size limits
                    chunk_size = 500
                    for i in range(0, len(unique_ids), chunk_size):
                        chunk = unique_ids[i:i + chunk_size]
                        placeholders = ",".join(["%s"] * len(chunk))
                        sql = f"SELECT id, syndicator_id FROM trc.sp_campaigns WHERE id IN ({placeholders})"
                        cursor.execute(sql, tuple(chunk))
                        for campaign_id, account_id in cursor.fetchall():
                            if campaign_id is not None and account_id is not None:
                                results[str(campaign_id)] = str(account_id)
                
                connection.close()
                
                # If we got results from MySQL, return them
                if results:
                    return results
                    
        except Exception as e:
            st.warning(f"MySQL connection failed, trying Vertica: {e}")

        # Try Vertica if MySQL failed or returned no results
        try:
            host = os.getenv("VERTICA_HOST") or ""
            port = int(os.getenv("VERTICA_PORT", "5433"))
            user = os.getenv("VERTICA_USER") or ""
            password = os.getenv("VERTICA_PASSWORD") or ""
            db = os.getenv("VERTICA_DB") or ""

            if host and user and password and db:
                connection = vertica_python.connect(
                    host=host,
                    port=port,
                    user=user,
                    password=password,
                    database=db,
                    autocommit=True,
                    connection_timeout=10,
                )
                
                with connection.cursor() as cursor:
                    # Process in chunks to avoid query size limits
                    chunk_size = 500
                    for i in range(0, len(unique_ids), chunk_size):
                        chunk = unique_ids[i:i + chunk_size]
                        placeholders = ",".join(["%s"] * len(chunk))
                        sql = f"SELECT id, syndicator_id FROM trc.sp_campaigns WHERE id IN ({placeholders})"
                        cursor.execute(sql, tuple(chunk))
                        for campaign_id, account_id in cursor.fetchall():
                            if campaign_id is not None and account_id is not None:
                                results[str(campaign_id)] = str(account_id)
                
                connection.close()
                
        except Exception as e:
            st.warning(f"Failed to fetch campaign accounts from both databases: {e}")

        return results

    def fetch_account_spend_data(self, account_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Fetch spend data for given account IDs (tries MySQL first, then Vertica)"""
        if not account_ids:
            return {}

        unique_ids = sorted({int(str(aid)) for aid in account_ids if str(aid).strip().isdigit()})
        if not unique_ids:
            return {}

        results: Dict[str, Dict[str, Any]] = {}
        
        # Try MySQL first
        try:
            host = os.getenv("MYSQL_HOST") or ""
            port = int(os.getenv("MYSQL_PORT", "3306"))
            user = os.getenv("MYSQL_USER") or ""
            password = os.getenv("MYSQL_PASSWORD") or ""
            db = os.getenv("MYSQL_DB") or ""

            if host and user and password and db:
                connection = pymysql.connect(
                    host=host,
                    port=port,
                    user=user,
                    password=password,
                    database=db,
                    charset="utf8mb4",
                    cursorclass=pymysql.cursors.Cursor,
                    autocommit=True,
                    read_timeout=60,
                    write_timeout=60,
                )
                
                with connection.cursor() as cursor:
                    # Process in chunks for better performance
                    chunk_size = 500
                    for i in range(0, len(unique_ids), chunk_size):
                        chunk = unique_ids[i:i + chunk_size]
                        placeholders = ",".join(["%s"] * len(chunk))
                        
                        # Query based on your provided SQL structure
                        sql = f"""
                        SELECT r.account_id, SUM(r.spent) AS total_spent, p.currency
                        FROM reports.advertiser_dimensions_by_request_time_report_daily r
                        JOIN trc.publishers p ON r.account_id = p.id
                        WHERE r.account_id IN ({placeholders})
                        GROUP BY r.account_id, p.currency
                        """
                        
                        cursor.execute(sql, tuple(chunk))
                        for account_id, total_spent, currency in cursor.fetchall():
                            if account_id is not None and total_spent is not None:
                                results[str(account_id)] = {
                                    'total_spent': float(total_spent),
                                    'currency': currency or 'USD'
                                }
                
                connection.close()
                
                # If we got results from MySQL, return them
                if results:
                    return results
                    
        except Exception as e:
            st.warning(f"MySQL spend lookup failed, trying Vertica: {e}")

        # Try Vertica if MySQL failed or returned no results
        try:
            host = os.getenv("VERTICA_HOST") or ""
            port = int(os.getenv("VERTICA_PORT", "5433"))
            user = os.getenv("VERTICA_USER") or ""
            password = os.getenv("VERTICA_PASSWORD") or ""
            db = os.getenv("VERTICA_DB") or ""

            if host and user and password and db:
                connection = vertica_python.connect(
                    host=host,
                    port=port,
                    user=user,
                    password=password,
                    database=db,
                    autocommit=True,
                    connection_timeout=10,
                )
                
                with connection.cursor() as cursor:
                    # Process in chunks for better performance
                    chunk_size = 500
                    for i in range(0, len(unique_ids), chunk_size):
                        chunk = unique_ids[i:i + chunk_size]
                        placeholders = ",".join(["%s"] * len(chunk))
                        
                        # Query based on your provided SQL structure
                        sql = f"""
                        SELECT r.account_id, SUM(r.spent) AS total_spent, p.currency
                        FROM reports.advertiser_dimensions_by_request_time_report_daily r
                        JOIN trc.publishers p ON r.account_id = p.id
                        WHERE r.account_id IN ({placeholders})
                        GROUP BY r.account_id, p.currency
                        """
                        
                        cursor.execute(sql, tuple(chunk))
                        for account_id, total_spent, currency in cursor.fetchall():
                            if account_id is not None and total_spent is not None:
                                results[str(account_id)] = {
                                    'total_spent': float(total_spent),
                                    'currency': currency or 'USD'
                                }
                
                connection.close()
                
        except Exception as e:
            st.warning(f"Failed to fetch spend data from both databases: {e}")

        return results

    def process_alerts_data(self, alerts: List[Dict[str, Any]]) -> pd.DataFrame:
        """Process raw alerts data into a structured DataFrame"""
        if not alerts:
            return pd.DataFrame()

        processed_alerts = []
        
        # Debug: Print structure of first alert to understand data format
        if alerts and len(alerts) > 0:
            st.info(f"🔍 Debug: Examining structure of first alert to fix missing fields...")
            first_alert = alerts[0]
            debug_info = []
            
            # Show all fields
            debug_info.append("**🔍 ALL AVAILABLE FIELDS:**")
            for key, value in first_alert.items():
                if isinstance(value, dict):
                    debug_info.append(f"**{key}**: dict with keys: {list(value.keys())}")
                    # Show nested content for important fields
                    if key.lower() in ['tag', 'campaign', 'project_name']:
                        for sub_key, sub_value in value.items():
                            debug_info.append(f"    └─ {sub_key}: {sub_value}")
                elif isinstance(value, list):
                    debug_info.append(f"**{key}**: list with {len(value)} items")
                    if value and len(value) > 0:
                        debug_info.append(f"    └─ first item: {value[0]}")
                else:
                    debug_info.append(f"**{key}**: {type(value).__name__} = {value}")
            
            # Look for fields that might contain campaign info
            debug_info.append("\n**🎯 CAMPAIGN-RELATED FIELDS:**")
            campaign_fields = [k for k in first_alert.keys() if any(word in k.lower() for word in ['campaign', 'ad', 'id'])]
            if campaign_fields:
                for field in campaign_fields:
                    debug_info.append(f"  ✓ {field}: {first_alert[field]}")
            else:
                debug_info.append("  ❌ No campaign-related fields found")
            
            # Look for fields that might contain URL info
            debug_info.append("\n**🌐 URL/TAG-RELATED FIELDS:**")
            url_fields = [k for k in first_alert.keys() if any(word in k.lower() for word in ['tag', 'url', 'landing', 'page'])]
            if url_fields:
                for field in url_fields:
                    debug_info.append(f"  ✓ {field}: {first_alert[field]}")
            else:
                debug_info.append("  ❌ No URL/tag-related fields found")
            
            with st.expander("🔧 Alert Data Structure (Debug Info)", expanded=True):
                st.markdown("\n".join(debug_info))
        
        for alert in alerts:
            try:
                # Extract project information
                project_names = alert.get('project_name', {})
                project_id = list(project_names.keys())[0] if project_names else None
                project_name = list(project_names.values())[0] if project_names else 'Unknown'

                # Extract location information
                location_data = alert.get('location', {})
                location_code = list(location_data.keys())[0] if location_data else 'Unknown'
                location_name = list(location_data.values())[0] if location_data else 'Unknown'

                # Extract tag information - handle multiple possible structures
                tag_url = 'Unknown'
                
                # Try all possible tag/URL field names
                possible_tag_fields = ['tag_url', 'tagUrl', 'tag', 'url', 'ad_url', 'adUrl', 'landing_page', 'landingPage']
                for field in possible_tag_fields:
                    if field in alert and alert[field]:
                        if isinstance(alert[field], dict):
                            # If it's a dict, try to get the first value
                            values = list(alert[field].values())
                            if values and values[0]:
                                tag_url = str(values[0])
                                break
                        elif isinstance(alert[field], str) and alert[field].strip():
                            tag_url = alert[field]
                            break
                
                # If still Unknown, try to extract from project name or other fields
                if tag_url == 'Unknown':
                    # Sometimes URL info is embedded in project names or other fields
                    project_name_full = project_name if project_name != 'Unknown' else ''
                    if 'LANDING-PAGE' in project_name_full or '_LANDING-PAGE_' in project_name_full:
                        # Extract URL-like info from project name
                        parts = project_name_full.split('_LANDING-PAGE_')
                        if len(parts) > 1:
                            tag_url = f"Landing page: {parts[1]}"

                # Extract campaign ID - check multiple possible field names and structures
                campaign_id = 'Unknown'
                
                # Try all possible campaign field names first
                possible_campaign_fields = ['campaign_id', 'campaignId', 'campaign', 'adCampaignId', 'ad_campaign_id']
                for field in possible_campaign_fields:
                    if field in alert and alert[field]:
                        if isinstance(alert[field], dict) and 'id' in alert[field]:
                            campaign_id = str(alert[field]['id'])
                            break
                        elif isinstance(alert[field], (str, int)) and str(alert[field]).strip():
                            campaign_id = str(alert[field])
                            break
                
                # If still Unknown, try to extract from project name patterns
                if campaign_id == 'Unknown' and project_name and project_name != 'Unknown':
                    # Pattern 1: SC_LANDING-PAGE_XXXXXXX_YYYYYYYY_ZZZZZZZZ
                    if '_LANDING-PAGE_' in project_name:
                        parts = project_name.split('_')
                        # Look for numeric parts that could be campaign IDs
                        numeric_parts = [part for part in parts if part.isdigit() and len(part) >= 6]
                        if numeric_parts:
                            # Take the first long numeric part as potential campaign ID
                            campaign_id = numeric_parts[0]
                    
                    # Pattern 2: projectname_campaignid_othernumbers
                    elif '_' in project_name:
                        parts = project_name.split('_')
                        # Look for parts that might be campaign IDs (6+ digits)
                        for part in parts:
                            if part.isdigit() and len(part) >= 6:
                                campaign_id = part
                                break
                
                # If still Unknown, try ad_id or other identifiers
                if campaign_id == 'Unknown':
                    if 'ad_id' in alert and alert['ad_id'] and str(alert['ad_id']).strip():
                        campaign_id = str(alert['ad_id'])
                    # Try any field that contains 'id' and might be campaign-related
                    elif any(field for field in alert.keys() if 'id' in field.lower() and alert[field]):
                        id_fields = [field for field in alert.keys() if 'id' in field.lower() and alert[field]]
                        if id_fields:
                            campaign_id = str(alert[id_fields[0]])

                processed_alert = {
                    'alert_id': alert.get('alert_id', ''),
                    'history_id': alert.get('history_id', ''),
                    'alert_name': alert.get('alert_name', ''),
                    'trigger_type_id': alert.get('trigger_type_id', ''),
                    'trigger_metadata': alert.get('trigger_metadata', ''),
                    'event_datetime': alert.get('event_datetime', ''),
                    'project_id': project_id,
                    'project_name': project_name,
                    'location_code': location_code,
                    'location_name': location_name,
                    'ad_id': alert.get('ad_id', ''),
                    'campaign_id': campaign_id,
                    'tag_url': tag_url,
                    'alert_details_url': alert.get('alert_details_url', ''),
                    'security_incident_urls': ','.join(alert.get('security_incident_urls', [])),
                }
                
                # Debug logging for first few alerts
                if len(processed_alerts) < 3:
                    st.write(f"**Alert {len(processed_alerts) + 1} Field Extraction:**")
                    st.write(f"  - Project Name: `{project_name}`")
                    st.write(f"  - Campaign ID extracted: `{campaign_id}` (from fields: {[f for f in possible_campaign_fields if f in alert]})")
                    st.write(f"  - Tag URL extracted: `{tag_url}` (from fields: {[f for f in possible_tag_fields if f in alert]})")
                    st.write(f"  - Available keys in alert: {list(alert.keys())}")
                    if campaign_id != 'Unknown':
                        st.write(f"  - ✅ Campaign ID successfully extracted!")
                    else:
                        st.write(f"  - ❌ No campaign ID found - will need database lookup or pattern extraction")
                
                processed_alerts.append(processed_alert)
                
            except Exception as e:
                st.warning(f"Error processing alert: {e}")
                continue

        return pd.DataFrame(processed_alerts)

    def enrich_with_project_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Enrich alerts DataFrame with project details"""
        if df.empty:
            return df

        # Get unique project IDs
        project_ids = df['project_id'].dropna().unique().tolist()
        
        if not project_ids:
            return df

        # Fetch project details
        project_details = self.fetch_project_details(project_ids)
        
        # Add project enrichment columns
        df['campaign_id'] = df['project_id'].map(
            lambda pid: project_details.get(pid, {}).get('ext_lineitem_id', 'Unknown')
        )
        df['auto_scan'] = df['project_id'].map(
            lambda pid: project_details.get(pid, {}).get('auto_scan', 'Unknown')
        )
        df['times_per_day'] = df['project_id'].map(
            lambda pid: project_details.get(pid, {}).get('times_per_day', 'Unknown')
        )
        df['scan_type'] = df['project_id'].map(
            lambda pid: project_details.get(pid, {}).get('scan_type', 'Unknown')
        )

        return df

    def fetch_available_locations(self) -> Dict[str, Any]:
        """Fetch available locations from GeoEdge API"""
        if not self.client:
            return {}

        try:
            locations = self.client.list_locations()
            return locations if locations else {}
        except Exception as e:
            st.warning(f"Could not fetch locations: {e}")
            return {}

    def analyze_location_options(self) -> Dict[str, Any]:
        """Analyze available location targeting options"""
        locations = self.fetch_available_locations()
        
        if not locations:
            return {
                'cities': [],
                'countries': [],
                'regions': [],
                'new_york_available': False,
                'city_level_targeting': False
            }
        
        # Get full location data from API
        try:
            data = self.client._request("GET", "/locations")
            response = data.get("response", {})
            locations_list = response.get("locations", [])
        except Exception:
            locations_list = []
        
        analysis = {
            'cities': [],
            'countries': [],
            'regions': [],
            'new_york_available': False,
            'city_level_targeting': False,
            'raw_locations': locations
        }
        
        # Analyze location data structure using the full API response
        for location_item in locations_list:
            if isinstance(location_item, dict):
                location_id = location_item.get('id')
                location_name = location_item.get('description', '')
                location_region = location_item.get('region', '')
                
                # Categorize by region type
                if 'Cities' in location_region:
                    analysis['cities'].append({
                        'id': location_id,
                        'name': location_name,
                        'region': location_region
                    })
                    analysis['city_level_targeting'] = True
                    
                    if 'New York' in location_name:
                        analysis['new_york_available'] = True
                        
                else:
                    # Countries and regions
                    analysis['countries'].append({
                        'id': location_id,
                        'name': location_name,
                        'region': location_region
                    })
        
        return analysis

    def create_unique_aggregations(self, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Create unique project and account aggregations with comma-separated values"""
        if df.empty:
            return df.copy(), df.copy()
        
        # Create unique alerts table (all alerts with details, account_id can be duplicate)
        unique_alerts_df = df.copy()
        
        # Create unique advertisers table (aggregated by account_id)
        if 'account_id' in df.columns:
            # Define the aggregation with only existing columns
            agg_dict = {
                'alert_id': lambda x: ', '.join(sorted(set(str(v) for v in x if pd.notna(v)))),
                'project_id': lambda x: ', '.join(sorted(set(str(v) for v in x if pd.notna(v)))),
                'project_name': lambda x: ', '.join(sorted(set(str(v) for v in x if pd.notna(v) and str(v) != 'Unknown'))),
                'trigger_type_id': lambda x: ', '.join(sorted(set(str(v) for v in x if pd.notna(v)))),
                'trigger_type_name': lambda x: ', '.join(sorted(set(str(v) for v in x if pd.notna(v)))),
                'location_code': lambda x: ', '.join(sorted(set(str(v) for v in x if pd.notna(v)))),
                'location_name': lambda x: ', '.join(sorted(set(str(v) for v in x if pd.notna(v)))),
                'event_datetime': ['min', 'max', 'count'],
                'alert_name': lambda x: ', '.join(sorted(set(str(v) for v in x if pd.notna(v)))),
            }
            
            # Add campaign_id if it exists
            if 'campaign_id' in df.columns:
                agg_dict['campaign_id'] = lambda x: ', '.join(sorted(set(str(v) for v in x if pd.notna(v))))
            
            # Add spend data if it exists
            if 'total_spent' in df.columns:
                agg_dict['total_spent'] = 'sum'
            if 'currency' in df.columns:
                agg_dict['currency'] = 'first'
            
            # Group by account_id and aggregate other fields
            advertiser_agg = df.groupby('account_id', dropna=False).agg(agg_dict).reset_index()
            
            # Flatten multi-level columns
            new_columns = ['account_id']
            for col in agg_dict.keys():
                if col == 'event_datetime':
                    new_columns.extend(['first_alert', 'last_alert', 'alert_count'])
                elif col == 'campaign_id' and 'campaign_id' in df.columns:
                    new_columns.append('campaign_ids')
                elif col == 'alert_id':
                    new_columns.append('alert_ids')
                elif col == 'project_id':
                    new_columns.append('project_ids')
                elif col == 'project_name':
                    new_columns.append('project_names')
                elif col == 'trigger_type_id':
                    new_columns.append('trigger_type_ids')
                elif col == 'trigger_type_name':
                    new_columns.append('trigger_type_names')
                elif col == 'location_code':
                    new_columns.append('location_codes')
                elif col == 'location_name':
                    new_columns.append('location_names')
                elif col == 'alert_name':
                    new_columns.append('alert_names')
                elif col == 'total_spent':
                    new_columns.append('total_spent')
                elif col == 'currency':
                    new_columns.append('currency')
            
            advertiser_agg.columns = new_columns
            unique_advertisers_df = advertiser_agg
        else:
            # If no account_id, group by project_id instead
            agg_dict = {
                'alert_id': lambda x: ', '.join(sorted(set(str(v) for v in x if pd.notna(v)))),
                'project_name': 'first',
                'trigger_type_id': lambda x: ', '.join(sorted(set(str(v) for v in x if pd.notna(v)))),
                'trigger_type_name': lambda x: ', '.join(sorted(set(str(v) for v in x if pd.notna(v)))),
                'location_code': lambda x: ', '.join(sorted(set(str(v) for v in x if pd.notna(v)))),
                'location_name': lambda x: ', '.join(sorted(set(str(v) for v in x if pd.notna(v)))),
                'event_datetime': ['min', 'max', 'count'],
                'alert_name': lambda x: ', '.join(sorted(set(str(v) for v in x if pd.notna(v)))),
            }
            
            # Add campaign_id if it exists
            if 'campaign_id' in df.columns:
                agg_dict['campaign_id'] = lambda x: ', '.join(sorted(set(str(v) for v in x if pd.notna(v))))
            
            project_agg = df.groupby('project_id', dropna=False).agg(agg_dict).reset_index()
            
            # Flatten multi-level columns
            new_columns = ['project_id', 'alert_ids', 'project_name']
            if 'campaign_id' in df.columns:
                new_columns.append('campaign_ids')
            new_columns.extend([
                'trigger_type_ids', 'trigger_type_names', 'location_codes', 'location_names',
                'first_alert', 'last_alert', 'alert_count', 'alert_names'
            ])
            
            project_agg.columns = new_columns
            unique_advertisers_df = project_agg
        
        return unique_alerts_df, unique_advertisers_df

    def enrich_with_trigger_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """Enrich alerts DataFrame with trigger type descriptions"""
        if df.empty:
            return df

        trigger_types = self.fetch_trigger_types()
        df['trigger_type_name'] = df['trigger_type_id'].map(
            lambda tid: trigger_types.get(str(tid), f'Unknown ({tid})')
        )

        return df


def main():
    st.set_page_config(
        page_title="GeoEdge Alerts Analysis Dashboard",
        page_icon="🚨",
        layout="wide"
    )

    st.title("🚨 GeoEdge Alerts Analysis Dashboard")
    st.caption("Analyze alerts from the last 90 days with project, campaign, and account mapping")

    # Initialize analyzer
    analyzer = AlertsAnalyzer()
    
    if not analyzer.client:
        st.error("❌ GeoEdge client not available. Please check your API credentials.")
        return

    # Sidebar controls
    with st.sidebar:
        st.header("🔧 Analysis Options")
        
        # Date range selection
        st.subheader("📅 Date Range")
        days_back = st.number_input(
            "Days to look back",
            min_value=1,
            max_value=90,
            value=7,
            help="Number of days to look back from today"
        )
        
        # Advanced filters
        st.subheader("🎯 Filters")
        
        specific_project_id = st.text_input(
            "Specific Project ID",
            placeholder="e.g., 1a755a2adf6301380b5ed35fb303767c",
            help="Filter by a specific project ID"
        )
        
        specific_alert_id = st.text_input(
            "Specific Alert ID",
            placeholder="e.g., 7d8a14b95a8418f3054492cfc5e2bfad",
            help="Filter by a specific alert ID"
        )
        
        trigger_type_filter = st.text_input(
            "Trigger Type ID",
            placeholder="e.g., 15",
            help="Filter by trigger type ID"
        )
        
        location_filter = st.text_input(
            "Location Codes",
            placeholder="e.g., US,CA,AU",
            help="Comma-separated location codes"
        )
        
        include_duplicates = st.checkbox(
            "Include duplicate alerts",
            value=False,
            help="Include all alerts instead of just unique ones"
        )
        
        max_alerts = st.number_input(
            "Maximum alerts to fetch",
            min_value=100,
            max_value=10000,
            value=1000,
            step=100,
            help="Maximum number of alerts to fetch"
        )
        
        # Database connection option
        st.subheader("Database Connection (for Campaign-Account Mapping)")
        enable_db = st.checkbox("Enable database lookup for campaign accounts", value=False)
        if enable_db:
            st.info("Will automatically try available database connections (MySQL/Vertica)")
        
        fetch_button = st.button("🔍 Fetch Alerts", type="primary", width="stretch")
        
        # Location Analysis Section
        st.subheader("🌍 Location Analysis")
        if st.button("🔍 Explore Available Locations", width="stretch"):
            with st.spinner("Analyzing available location targeting options..."):
                location_analysis = analyzer.analyze_location_options()
                
                if location_analysis.get('raw_locations'):
                    st.success("✅ Location data retrieved!")
                    
                    # Show summary
                    st.markdown("### 📊 Location Targeting Summary")
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Cities Available", len(location_analysis.get('cities', [])))
                        if location_analysis.get('new_york_available'):
                            st.success("✅ New York targeting available")
                        else:
                            st.warning("❌ New York targeting not found")
                    
                    with col2:
                        st.metric("Countries Available", len(location_analysis.get('countries', [])))
                        if location_analysis.get('city_level_targeting'):
                            st.success("✅ City-level targeting supported")
                        else:
                            st.warning("❌ Only country-level targeting")
                    
                    with col3:
                        st.metric("Regions Available", len(location_analysis.get('regions', [])))
                    
                    # Show detailed location data
                    with st.expander("🌍 Available Cities", expanded=location_analysis.get('city_level_targeting', False)):
                        if location_analysis.get('cities'):
                            cities_df = pd.DataFrame(location_analysis['cities'])
                            st.dataframe(cities_df, width="stretch")
                        else:
                            st.info("No city-level locations found")
                    
                    with st.expander("🌎 Available Countries"):
                        if location_analysis.get('countries'):
                            countries_df = pd.DataFrame(location_analysis['countries'])
                            st.dataframe(countries_df, width="stretch")
                        else:
                            st.info("No country-level locations found")
                    
                    with st.expander("🌏 Available Regions"):
                        if location_analysis.get('regions'):
                            regions_df = pd.DataFrame(location_analysis['regions'])
                            st.dataframe(regions_df, width="stretch")
                        else:
                            st.info("No regional locations found")
                    
                    # Show raw location data for debugging
                    with st.expander("🔧 Raw Location Data (Debug)"):
                        st.json(location_analysis.get('raw_locations', {}))
                        
                    # Answer user's specific question
                    st.markdown("### 🎯 Targeting New York vs US")
                    if location_analysis.get('new_york_available'):
                        st.success("✅ **Yes, you can target New York specifically!** Use the New York location ID instead of 'US' for city-level targeting.")
                        ny_locations = [loc for loc in location_analysis.get('cities', []) if 'new york' in loc.get('name', '').lower()]
                        if ny_locations:
                            st.info(f"New York location details: {ny_locations[0]}")
                    else:
                        if location_analysis.get('city_level_targeting'):
                            st.warning("⚠️ New York not found, but other cities are available. Check the cities list above.")
                        else:
                            st.error("❌ Only country-level targeting (like 'US') is available. City-level targeting like 'New York' is not supported.")
                else:
                    st.error("❌ Could not retrieve location data from GeoEdge API")

    # Main content area
    if fetch_button:
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        min_datetime = start_date.strftime("%Y-%m-%d %H:%M:%S")
        max_datetime = end_date.strftime("%Y-%m-%d %H:%M:%S")
        
        # Parse filters
        location_ids = [loc.strip() for loc in location_filter.split(",")] if location_filter else None
        
        st.info(f"🔍 Fetching alerts from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Fetch alerts
        st.info(f"🔍 Fetching alerts from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Create progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Step 1: Fetch alerts from API
        status_text.text("🌐 Connecting to GeoEdge API...")
        progress_bar.progress(10)
        
        alerts = analyzer.fetch_alerts_history(
            min_datetime=min_datetime,
            max_datetime=max_datetime,
            project_id=specific_project_id.strip() if specific_project_id else None,
            alert_id=specific_alert_id.strip() if specific_alert_id else None,
            trigger_type_id=trigger_type_filter.strip() if trigger_type_filter else None,
            location_ids=location_ids,
            full_raw=include_duplicates,
            limit=max_alerts
        )
        
        progress_bar.progress(30)
        status_text.text(f"✅ Fetched {len(alerts)} alerts from API")
        time.sleep(0.5)  # Brief pause to show progress
        
        if not alerts:
            progress_bar.progress(100)
            status_text.text("⚠️ No alerts found matching your criteria")
            st.warning("⚠️ No alerts found matching your criteria.")
            return
        
        # Step 2: Process alerts data
        progress_bar.progress(40)
        status_text.text("📊 Processing alerts data...")
        
        df = analyzer.process_alerts_data(alerts)
        
        if df.empty:
            progress_bar.progress(100)
            status_text.text("⚠️ No valid alert data could be processed")
            st.warning("⚠️ No valid alert data could be processed.")
            return
        
        # Step 3: Enrich with project data
        progress_bar.progress(60)
        status_text.text("🏗️ Enriching with project details...")
        
        df = analyzer.enrich_with_project_data(df)
        
        # Step 4: Enrich with trigger types
        progress_bar.progress(70)
        status_text.text("🎯 Adding trigger type descriptions...")
        
        df = analyzer.enrich_with_trigger_types(df)
        
        # Step 5: Enrich with campaign-account mapping if database is enabled
        if enable_db and 'campaign_id' in df.columns:
            progress_bar.progress(80)
            status_text.text("🔍 Looking up campaign accounts in database...")
            
            campaign_ids = df['campaign_id'].dropna().unique().tolist()
            if campaign_ids:
                campaign_accounts = analyzer.fetch_campaign_accounts_from_db(campaign_ids)
                df['account_id'] = df['campaign_id'].map(campaign_accounts)
                status_text.text(f"✅ Found account mappings for {len(campaign_accounts)} campaigns")
                
                # Fetch spend data for accounts
                progress_bar.progress(85)
                status_text.text("💰 Looking up spend data for accounts...")
                
                account_ids = df['account_id'].dropna().unique().tolist()
                if account_ids:
                    spend_data = analyzer.fetch_account_spend_data(account_ids)
                    df['total_spent'] = df['account_id'].map(lambda x: spend_data.get(str(x), {}).get('total_spent', 0) if pd.notna(x) else 0)
                    df['currency'] = df['account_id'].map(lambda x: spend_data.get(str(x), {}).get('currency', 'USD') if pd.notna(x) else 'USD')
                    status_text.text(f"💰 Found spend data for {len(spend_data)} accounts")
                else:
                    status_text.text("ℹ️ No account IDs found for spend lookup")
            else:
                status_text.text("ℹ️ No campaign IDs found for account lookup")
        
        # Step 6: Create unique aggregations
        progress_bar.progress(90)
        status_text.text("📋 Creating unique data views...")
        
        unique_alerts_df, unique_advertisers_df = analyzer.create_unique_aggregations(df)
        
        # Complete
        progress_bar.progress(100)
        status_text.text(f"✅ Completed! Processed {len(alerts)} alerts into {len(unique_alerts_df)} unique alerts and {len(unique_advertisers_df)} unique advertisers")
        time.sleep(1)  # Show completion message briefly
        
        # Clear progress indicators
        progress_bar.empty()
        status_text.empty()
        
        # Store in session state
        st.session_state['alerts_df'] = df
        st.session_state['raw_alerts'] = alerts

    # Display results if available
    if 'alerts_df' in st.session_state:
        df = st.session_state['alerts_df']
        
        # Summary metrics
        st.markdown("### 📊 Summary Metrics")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Alerts", len(df))
        with col2:
            unique_projects = df['project_id'].nunique()
            st.metric("Unique Projects", unique_projects)
        with col3:
            unique_triggers = df['trigger_type_id'].nunique()
            st.metric("Trigger Types", unique_triggers)
        with col4:
            unique_locations = df['location_code'].nunique()
            st.metric("Locations", unique_locations)

        # Filter options
        st.markdown("### 🔍 Filter Results")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            alert_name_filter = st.multiselect(
                "Alert Names",
                options=sorted(df['alert_name'].unique()),
                help="Filter by alert names"
            )
        
        with col2:
            trigger_type_filter = st.multiselect(
                "Trigger Types",
                options=sorted(df['trigger_type_name'].unique()),
                help="Filter by trigger types"
            )
        
        with col3:
            location_filter = st.multiselect(
                "Locations",
                options=sorted(df['location_name'].unique()),
                help="Filter by locations"
            )

        # Search functionality
        search_term = st.text_input(
            "🔍 Search in all fields",
            placeholder="Search project names, URLs, alert details..."
        )

        # Apply filters
        filtered_df = df.copy()
        
        if alert_name_filter:
            filtered_df = filtered_df[filtered_df['alert_name'].isin(alert_name_filter)]
        
        if trigger_type_filter:
            filtered_df = filtered_df[filtered_df['trigger_type_name'].isin(trigger_type_filter)]
        
        if location_filter:
            filtered_df = filtered_df[filtered_df['location_name'].isin(location_filter)]
        
        if search_term:
            search_mask = (
                filtered_df['project_name'].str.contains(search_term, case=False, na=False) |
                filtered_df['tag_url'].str.contains(search_term, case=False, na=False) |
                filtered_df['alert_name'].str.contains(search_term, case=False, na=False) |
                filtered_df['trigger_metadata'].str.contains(search_term, case=False, na=False)
            )
            filtered_df = filtered_df[search_mask]

        # Data Display section with improved presentation
        st.markdown("### � Data Analysis")
        
        # Apply filters to unique data
        filtered_alerts_df = unique_alerts_df.copy()
        filtered_advertisers_df = unique_advertisers_df.copy()
        
        # Apply search filter if provided
        if search_term:
            search_mask = (
                filtered_alerts_df['alert_name'].str.contains(search_term, case=False, na=False) |
                filtered_alerts_df['trigger_metadata'].str.contains(search_term, case=False, na=False) |
                filtered_alerts_df['project_name'].str.contains(search_term, case=False, na=False)
            )
            filtered_alerts_df = filtered_alerts_df[search_mask]
        
        # Create main tabs for different views
        data_tab1, data_tab2, analytics_tab = st.tabs([
            f"🚨 All Alerts ({len(filtered_alerts_df)})", 
            f"🏢 Unique Advertisers ({len(filtered_advertisers_df)})", 
            "📈 Analytics & Insights"
        ])
        
        with data_tab1:
            st.markdown("#### 🚨 Complete Alerts Table")
            st.markdown("*Shows all individual alerts with complete details. Account IDs may appear multiple times.*")
            
            # Display main alerts table
            alerts_display_columns = [
                'event_datetime', 'alert_name', 'trigger_type_name', 'project_name',
                'location_name', 'trigger_metadata', 'campaign_id', 'tag_url'
            ]
            
            # Add account_id if available
            if 'account_id' in filtered_alerts_df.columns:
                alerts_display_columns.insert(-1, 'account_id')
            
            # Add row numbers
            filtered_alerts_display = filtered_alerts_df[alerts_display_columns].copy()
            filtered_alerts_display.insert(0, 'Row', range(1, len(filtered_alerts_display) + 1))
            
            # Column configuration for alerts table
            alerts_column_config = {
                'Row': st.column_config.NumberColumn('Row', width='small'),
                'event_datetime': st.column_config.DatetimeColumn('Event Time', width='medium'),
                'alert_name': st.column_config.TextColumn('Alert Name', width='medium'),
                'trigger_type_name': st.column_config.TextColumn('Trigger Type', width='medium'),
                'project_name': st.column_config.TextColumn('Project Name', width='large'),
                'location_name': st.column_config.TextColumn('Location', width='small'),
                'trigger_metadata': st.column_config.TextColumn('Details', width='medium'),
                'campaign_id': st.column_config.TextColumn('Campaign ID', width='small'),
                'tag_url': st.column_config.LinkColumn('Tag URL', width='large'),
            }
            
            if 'account_id' in filtered_alerts_df.columns:
                alerts_column_config['account_id'] = st.column_config.TextColumn('Account ID', width='small')
            
            st.dataframe(
                filtered_alerts_display,
                width="stretch",
                column_config=alerts_column_config,
                hide_index=True,
                height=400
            )
            
            # Quick stats for alerts
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Alerts", len(filtered_alerts_df))
            with col2:
                st.metric("Unique Projects", filtered_alerts_df['project_id'].nunique())
            with col3:
                st.metric("Unique Trigger Types", filtered_alerts_df['trigger_type_id'].nunique())
            with col4:
                if 'account_id' in filtered_alerts_df.columns:
                    st.metric("Unique Accounts", filtered_alerts_df['account_id'].nunique())
                else:
                    st.metric("Unique Locations", filtered_alerts_df['location_code'].nunique())
        
        with data_tab2:
            st.markdown("#### 🏢 Unique Advertisers/Accounts Summary")
            st.markdown("*Aggregated view showing unique advertisers with all associated data grouped together.*")
            
            if not filtered_advertisers_df.empty:
                # Add row numbers to advertisers table
                advertisers_display = filtered_advertisers_df.copy()
                advertisers_display.insert(0, 'Row', range(1, len(advertisers_display) + 1))
                
                # Configure columns for advertisers table
                advertisers_column_config = {
                    'Row': st.column_config.NumberColumn('Row', width='small'),
                    'alert_count': st.column_config.NumberColumn('Alert Count', width='small'),
                    'first_alert': st.column_config.DatetimeColumn('First Alert', width='medium'),
                    'last_alert': st.column_config.DatetimeColumn('Last Alert', width='medium'),
                    'alert_names': st.column_config.TextColumn('Alert Types', width='large'),
                    'trigger_type_names': st.column_config.TextColumn('Trigger Types', width='large'),
                    'project_names': st.column_config.TextColumn('Projects', width='large'),
                    'location_names': st.column_config.TextColumn('Locations', width='medium'),
                }
                
                # Add account_id column if available
                if 'account_id' in filtered_advertisers_df.columns:
                    advertisers_column_config['account_id'] = st.column_config.TextColumn('Account ID', width='small')
                    
                st.dataframe(
                    advertisers_display,
                    width="stretch",
                    column_config=advertisers_column_config,
                    hide_index=True,
                    height=400
                )
                
                # Quick stats for advertisers
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Unique Advertisers", len(filtered_advertisers_df))
                with col2:
                    avg_alerts = filtered_advertisers_df['alert_count'].mean()
                    st.metric("Avg Alerts per Advertiser", f"{avg_alerts:.1f}")
                with col3:
                    max_alerts = filtered_advertisers_df['alert_count'].max()
                    st.metric("Max Alerts (Single Advertiser)", max_alerts)
                with col4:
                    if 'project_names' in filtered_advertisers_df.columns:
                        total_unique_projects = len(set(pid for pids in filtered_advertisers_df['project_names'] for pid in str(pids).split(', ') if pid.strip()))
                        st.metric("Total Unique Projects", total_unique_projects)
                    else:
                        st.metric("Unique Projects", filtered_advertisers_df['project_id'].nunique() if 'project_id' in filtered_advertisers_df.columns else 0)
            else:
                st.info("No advertiser data available (database lookup required for account aggregation)")
        
        with analytics_tab:
            st.markdown("#### 📈 Enhanced Analytics & Insights")
            
            # Use filtered alerts data for analytics
            analytics_df = filtered_alerts_df
            
            # Enhanced Analytics with insights
            st.markdown("#### 🔍 Key Insights")
            
            # Key insights section
            insights_col1, insights_col2, insights_col3 = st.columns(3)
            
            with insights_col1:
                st.metric("Total Alerts", len(analytics_df))
                if 'account_id' in analytics_df.columns:
                    st.metric("Unique Accounts", analytics_df['account_id'].nunique())
                else:
                    st.metric("Unique Projects", analytics_df['project_id'].nunique())
            
            with insights_col2:
                most_common_trigger = analytics_df['trigger_type_name'].mode().iloc[0] if not analytics_df.empty else "N/A"
                st.metric("Most Common Trigger", most_common_trigger)
                st.metric("Unique Trigger Types", analytics_df['trigger_type_id'].nunique())
            
            with insights_col3:
                if not analytics_df.empty:
                    date_range = (pd.to_datetime(analytics_df['event_datetime']).max() - pd.to_datetime(analytics_df['event_datetime']).min()).days
                    st.metric("Date Range (Days)", date_range)
                    avg_daily = len(analytics_df) / max(date_range, 1)
                    st.metric("Avg Alerts/Day", f"{avg_daily:.1f}")
                else:
                    st.metric("Date Range", "N/A")
                    st.metric("Avg Alerts/Day", "N/A")
            
            # Detailed Analytics Tabs
            analytics_tab1, analytics_tab2, analytics_tab3 = st.tabs([
                "🎯 Trigger Analysis", 
                "📍 Location Analysis", 
                "⏰ Time Analysis"
            ])
            
            with analytics_tab1:
                st.markdown("#### 🎯 Alert Trigger Patterns")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Top Alert Triggers**")
                    trigger_counts = analytics_df['trigger_type_name'].value_counts().head(10)
                    st.bar_chart(trigger_counts)
                    
                    # Show top triggers with percentages
                    st.markdown("**Trigger Type Breakdown:**")
                    for trigger, count in trigger_counts.head(5).items():
                        percentage = (count / len(analytics_df)) * 100
                        st.write(f"• {trigger}: {count} ({percentage:.1f}%)")
                
                with col2:
                    st.markdown("**Alert Names Distribution**")
                    alert_counts = analytics_df['alert_name'].value_counts().head(10)
                    st.bar_chart(alert_counts)
                    
                    # Show most problematic alerts
                    st.markdown("**Most Frequent Alerts:**")
                    for alert, count in alert_counts.head(5).items():
                        percentage = (count / len(analytics_df)) * 100
                        st.write(f"• {alert}: {count} ({percentage:.1f}%)")
            
            with analytics_tab2:
                st.markdown("#### 📍 Geographic Distribution")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Alerts by Location**")
                    location_counts = analytics_df['location_name'].value_counts().head(15)
                    st.bar_chart(location_counts)
                    
                    # Location insights
                    st.markdown("**Top Affected Locations:**")
                    for location, count in location_counts.head(5).items():
                        percentage = (count / len(analytics_df)) * 100
                        st.write(f"• {location}: {count} ({percentage:.1f}%)")
                
                with col2:
                    st.markdown("**Project Distribution**")
                    project_counts = analytics_df['project_name'].value_counts().head(10)
                    st.bar_chart(project_counts)
                    
                    # Project insights
                    st.markdown("**Most Affected Projects:**")
                    for project, count in project_counts.head(5).items():
                        percentage = (count / len(analytics_df)) * 100
                        st.write(f"• {project}: {count} ({percentage:.1f}%)")
            
            with analytics_tab3:
                st.markdown("#### ⏰ Temporal Analysis")
                
                # Convert datetime for analysis
                time_df = analytics_df.copy()
                time_df['event_datetime'] = pd.to_datetime(time_df['event_datetime'])
                time_df['date'] = time_df['event_datetime'].dt.date
                time_df['hour'] = time_df['event_datetime'].dt.hour
                time_df['day_of_week'] = time_df['event_datetime'].dt.day_name()
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Daily Alert Trends**")
                    daily_counts = time_df.groupby('date').size()
                    st.line_chart(daily_counts)
                    
                    # Peak day analysis
                    peak_day = daily_counts.idxmax() if not daily_counts.empty else None
                    peak_count = daily_counts.max() if not daily_counts.empty else 0
                    st.write(f"**Peak Day:** {peak_day} ({peak_count} alerts)")
                
                with col2:
                    st.markdown("**Hourly Distribution**")
                    hourly_counts = time_df['hour'].value_counts().sort_index()
                    st.bar_chart(hourly_counts)
                    
                    # Peak hour analysis
                    peak_hour = hourly_counts.idxmax() if not hourly_counts.empty else 0
                    peak_hour_count = hourly_counts.max() if not hourly_counts.empty else 0
                    st.write(f"**Peak Hour:** {peak_hour}:00 ({peak_hour_count} alerts)")
                
                # Day of week analysis
                st.markdown("**Weekly Pattern**")
                weekly_counts = time_df['day_of_week'].value_counts()
                # Reorder by weekday
                days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                weekly_counts = weekly_counts.reindex([day for day in days_order if day in weekly_counts.index])
                st.bar_chart(weekly_counts)

        # Export options
        st.markdown("### 💾 Export Options")
        
        export_col1, export_col2, export_col3, export_col4 = st.columns(4)
        
        with export_col1:
            csv_data = filtered_alerts_df.to_csv(index=False)
            st.download_button(
                label="📄 All Alerts CSV",
                data=csv_data,
                file_name=f"geoedge_alerts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                help="Download all individual alerts as CSV"
            )
        
        with export_col2:
            if not filtered_advertisers_df.empty:
                advertisers_csv = filtered_advertisers_df.to_csv(index=False)
                st.download_button(
                    label="🏢 Advertisers CSV",
                    data=advertisers_csv,
                    file_name=f"geoedge_advertisers_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    help="Download unique advertisers summary as CSV"
                )
            else:
                st.button("🏢 Advertisers CSV", disabled=True, help="No advertiser data available")
        
        with export_col3:
            json_data = filtered_alerts_df.to_json(orient='records', date_format='iso')
            st.download_button(
                label="📋 Alerts JSON",
                data=json_data,
                file_name=f"geoedge_alerts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                help="Download alerts data as JSON"
            )
        
        with export_col4:
            raw_json = json.dumps(alerts, indent=2)
            st.download_button(
                label="🔧 Raw API Data",
                data=raw_json,
                file_name=f"geoedge_alerts_raw_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                help="Download raw API response data"
            )

        # Detailed view section
        st.markdown("### 🔍 Detailed Alert View")
        if not filtered_df.empty:
            selected_row = st.selectbox(
                "Select an alert to view details:",
                options=range(len(filtered_df)),
                format_func=lambda x: f"Row {x+1}: {filtered_df.iloc[x]['alert_name']} - {filtered_df.iloc[x]['project_name']}"
            )
            
            selected_alert = filtered_df.iloc[selected_row]
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Alert Information")
                st.write(f"**Alert ID:** {selected_alert['alert_id']}")
                st.write(f"**History ID:** {selected_alert['history_id']}")
                st.write(f"**Alert Name:** {selected_alert['alert_name']}")
                st.write(f"**Trigger Type:** {selected_alert['trigger_type_name']}")
                st.write(f"**Event Time:** {selected_alert['event_datetime']}")
                st.write(f"**Metadata:** {selected_alert['trigger_metadata']}")
            
            with col2:
                st.markdown("#### Project Information")
                st.write(f"**Project ID:** {selected_alert['project_id']}")
                st.write(f"**Project Name:** {selected_alert['project_name']}")
                st.write(f"**Campaign ID:** {selected_alert['campaign_id']}")
                st.write(f"**Location:** {selected_alert['location_name']} ({selected_alert['location_code']})")
                st.write(f"**Tag URL:** {selected_alert['tag_url']}")
            
            if selected_alert['alert_details_url']:
                st.markdown("#### Additional Resources")
                st.markdown(f"[🔗 View Alert Details]({selected_alert['alert_details_url']})")
            
            if selected_alert['security_incident_urls']:
                st.markdown("#### Security Incident URLs")
                urls = selected_alert['security_incident_urls'].split(',')
                for url in urls:
                    if url.strip():
                        st.markdown(f"[🚨 Security URL]({url.strip()})")

    else:
        st.info("👆 Use the sidebar controls to fetch and analyze GeoEdge alerts.")
        
        # Show some helpful information
        st.markdown("### 📚 About This Dashboard")
        st.markdown("""
        This dashboard allows you to:
        
        - **Fetch alerts** from the GeoEdge API for the last 90 days
        - **Filter by various criteria** including project ID, alert ID, trigger types, and locations
        - **Analyze alert patterns** by trigger type, location, and time
        - **Export data** in multiple formats (CSV, JSON, raw API data)
        - **View detailed information** for individual alerts
        - **Track project relationships** with campaign and account mapping
        
        **Getting Started:**
        1. Set your desired date range in the sidebar
        2. Optionally add filters to narrow down results
        3. Click "Fetch Alerts" to retrieve data
        4. Use the filtering and search options to analyze results
        5. Export data for further analysis
        """)


if __name__ == "__main__":
    main()