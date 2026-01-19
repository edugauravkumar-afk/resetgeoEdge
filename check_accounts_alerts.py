#!/usr/bin/env python3
"""
Check alerts for specific account IDs in the last 90 days.
Creates an Excel sheet with detailed alert information per account.
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Any
from collections import defaultdict

import pandas as pd
from dotenv import load_dotenv

from geoedge_projects.client import GeoEdgeClient

# Load environment
load_dotenv()


def extract_threat_info(alert: Dict[str, Any]) -> Dict[str, Any]:
    """Extract detailed threat information from alert (actual GeoEdge structure)"""
    threat_info = {
        'trigger_metadata': None,  # Contains threat type like "Financial Scam", "Malicious Domain"
        'security_incident_urls': None,  # List of malicious/security URLs
        'alert_details_url': None,  # Link to full alert details
        'has_security_urls': False,
        'security_url_count': 0,
        'threat_category': None
    }
    
    # Extract trigger_metadata (this contains threat type)
    trigger_metadata = alert.get('trigger_metadata')
    if trigger_metadata:
        threat_info['trigger_metadata'] = trigger_metadata
        threat_info['threat_category'] = trigger_metadata
    
    # Extract security incident URLs
    security_urls = alert.get('security_incident_urls', [])
    if security_urls and len(security_urls) > 0:
        threat_info['has_security_urls'] = True
        threat_info['security_url_count'] = len(security_urls)
        threat_info['security_incident_urls'] = '; '.join(security_urls[:3])  # First 3 URLs
    
    # Extract alert details URL
    alert_details = alert.get('alert_details_url')
    if alert_details:
        threat_info['alert_details_url'] = alert_details
    
    return threat_info


def get_campaign_account_mapping(account_ids: List[str]) -> Dict[str, str]:
    """Get campaign to account mapping from database"""
    import pymysql
    
    host = os.getenv("MYSQL_HOST")
    port = int(os.getenv("MYSQL_PORT", "3306"))
    user = os.getenv("MYSQL_USER")
    password = os.getenv("MYSQL_PASSWORD")
    db = os.getenv("MYSQL_DB")
    
    campaign_to_account = {}
    
    if not all([host, user, password, db]):
        print("⚠️ Database credentials not found, skipping campaign-account mapping")
        return campaign_to_account
    
    try:
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
        
        print(f"📊 Fetching campaigns for {len(account_ids)} accounts from database...")
        
        with connection.cursor() as cursor:
            # Get all campaigns for these accounts
            placeholders = ",".join(["%s"] * len(account_ids))
            sql = f"SELECT id, syndicator_id FROM trc.sp_campaigns WHERE syndicator_id IN ({placeholders})"
            cursor.execute(sql, tuple(account_ids))
            
            for campaign_id, account_id in cursor.fetchall():
                if campaign_id and account_id:
                    campaign_to_account[str(campaign_id)] = str(account_id)
        
        connection.close()
        print(f"✅ Found {len(campaign_to_account)} campaigns for these accounts")
        
    except Exception as e:
        print(f"❌ Database error: {e}")
    
    return campaign_to_account


def main():
    # Account IDs to check
    account_ids = [
        "1290644", "1466060", "1835770", "1623554", "1756429", "1855313", "1724820",
        "1639660", "1786547", "1527715", "1243928", "1343639", "1341693", "1880307",
        "1756440", "1782473", "1487226", "1457895", "1905088", "1154814", "1847769",
        "1878595", "1887104", "1341694", "1343644", "1401160", "1474131", "1204587",
        "1829970", "1828308", "1642145", "1702248", "1829976", "1040822", "1341695",
        "1784283", "1562293", "1892692", "1008114", "1827440", "1896474", "1896475",
        "1896473", "1787788", "1878691", "1688532", "1702259", "1593978", "1077096",
        "1162266", "1510736", "1691715", "1524612", "1661493", "1878358", "1421191",
        "1071765", "1705266", "1154809", "1688849", "1775713", "1798665", "1813041",
        "1756427", "1693504", "1813037", "1601637", "1902380", "1878765", "1243922",
        "1881185", "1147892", "1891323", "1878359", "1661494", "1718765", "1823276",
        "1895053", "1896927", "1784361", "1896472", "1702256", "1039024", "1341696",
        "1900040", "1874354", "1171184", "1766414", "1878372", "1908584", "1894751",
        "1162263", "1346833", "1243926", "1907682", "1535686", "1867619"
    ]
    
    print(f"🔍 Checking alerts for {len(account_ids)} accounts in the last 90 days...")
    print(f"📅 Date range: {(datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}")
    
    # Initialize GeoEdge client
    try:
        client = GeoEdgeClient()
        print("✅ GeoEdge client initialized")
    except Exception as e:
        print(f"❌ Failed to initialize GeoEdge client: {e}")
        return
    
    # Get campaign to account mapping
    campaign_to_account = get_campaign_account_mapping(account_ids)
    
    # Calculate date range (last 90 days)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    min_datetime = start_date.strftime("%Y-%m-%d %H:%M:%S")
    max_datetime = end_date.strftime("%Y-%m-%d %H:%M:%S")
    
    # Fetch alerts in smaller chunks (30 days at a time to avoid timeout)
    # Use full_raw=1 to get detailed metadata including malicious domain info
    print(f"\n🌐 Fetching alerts from GeoEdge API in 30-day chunks (with full metadata)...")
    all_alerts = []
    
    try:
        # Split into 3 periods of 30 days each
        for period in range(3):
            period_end = end_date - timedelta(days=period * 30)
            period_start = period_end - timedelta(days=30)
            period_min = period_start.strftime("%Y-%m-%d %H:%M:%S")
            period_max = period_end.strftime("%Y-%m-%d %H:%M:%S")
            
            print(f"  Period {period + 1}/3: {period_start.strftime('%Y-%m-%d')} to {period_end.strftime('%Y-%m-%d')}")
            period_alerts = []
            
            try:
                for alert in client.iter_alerts_history(
                    min_datetime=period_min,
                    max_datetime=period_max,
                    full_raw=1,  # Get full metadata
                    page_limit=5000,
                    max_pages=50
                ):
                    period_alerts.append(alert)
                    
                    if len(period_alerts) % 1000 == 0:
                        print(f"    Fetched {len(period_alerts)} alerts in this period...")
                
                all_alerts.extend(period_alerts)
                print(f"  ✅ Period {period + 1}: {len(period_alerts)} alerts")
            
            except Exception as e:
                print(f"  ⚠️ Error in period {period + 1}: {e}")
                continue
    
    except Exception as e:
        print(f"❌ Error fetching alerts: {e}")
        if not all_alerts:
            return
    
    print(f"✅ Total alerts fetched: {len(all_alerts)}")
    
    # Get project details to extract campaign IDs
    print(f"\n📋 Processing alerts and extracting project/campaign information...")
    
    # Group alerts by account
    account_alerts = defaultdict(list)
    account_projects = defaultdict(set)
    account_campaigns = defaultdict(set)
    account_alert_types = defaultdict(lambda: defaultdict(int))  # account_id -> {alert_type: count}
    account_threats = defaultdict(list)  # Store detailed threat info per account
    
    # Process each alert
    for alert in all_alerts:
        # Extract project info
        project_names = alert.get('project_name', {})
        project_id = list(project_names.keys())[0] if project_names else None
        project_name = list(project_names.values())[0] if project_names else 'Unknown'
        
        # Try to extract campaign ID from project name (format: SC_LANDING-PAGE_1854664_46925876_418916639)
        campaign_id = None
        if project_name and '_' in project_name:
            parts = project_name.split('_')
            for part in parts:
                if part.isdigit() and len(part) >= 7:  # Campaign IDs are typically 7+ digits
                    if part in campaign_to_account:
                        campaign_id = part
                        break
        
        # Map to account
        if campaign_id and campaign_id in campaign_to_account:
            account_id = campaign_to_account[campaign_id]
            
            if account_id in account_ids:
                alert_name = alert.get('alert_name', 'Unknown')
                
                # Extract threat information
                threat_info = extract_threat_info(alert)
                
                alert_data = {
                    'alert_id': alert.get('alert_id', 'Unknown'),
                    'project_id': project_id,
                    'project_name': project_name,
                    'campaign_id': campaign_id,
                    'event_datetime': alert.get('event_datetime', 'Unknown'),
                    'trigger_type_id': alert.get('trigger_type_id', 'Unknown'),
                    'alert_name': alert_name,
                    'location': list(alert.get('location', {}).values())[0] if alert.get('location') else 'Unknown',
                    **threat_info  # Add all threat info fields
                }
                
                account_alerts[account_id].append(alert_data)
                account_projects[account_id].add(project_name)
                account_campaigns[account_id].add(campaign_id)
                account_alert_types[account_id][alert_name] += 1
                
                # Store threat details if present (has security URLs or threat category)
                if threat_info['has_security_urls'] or threat_info['threat_category']:
                    account_threats[account_id].append({
                        'alert_id': alert.get('alert_id', 'Unknown'),
                        'project_name': project_name,
                        'campaign_id': campaign_id,
                        'alert_name': alert_name,
                        'event_datetime': alert.get('event_datetime', 'Unknown'),
                        **threat_info
                    })
    
    print(f"✅ Processed {len(all_alerts)} alerts")
    print(f"📊 Found alerts for {len(account_alerts)} accounts out of {len(account_ids)} provided")
    
    # Create detailed report
    print(f"\n📄 Creating Excel report...")
    
    # Prepare data for Excel
    report_data = []
    
    for account_id in account_ids:
        alerts = account_alerts.get(account_id, [])
        has_alerts = len(alerts) > 0
        
        # Get alert type breakdown
        alert_types_str = ""
        if has_alerts and account_id in account_alert_types:
            alert_types = account_alert_types[account_id]
            alert_types_str = ", ".join([f"{name}: {count}" for name, count in sorted(alert_types.items(), key=lambda x: -x[1])])
        
        report_data.append({
            'Account ID': account_id,
            'Has Alerts (Last 90 Days)': 'YES' if has_alerts else 'NO',
            'Total Alerts': len(alerts),
            'Unique Projects': len(account_projects.get(account_id, set())),
            'Unique Campaigns': len(account_campaigns.get(account_id, set())),
            'Alert Types Breakdown': alert_types_str,
            'Projects': ', '.join(sorted(account_projects.get(account_id, set()))) if has_alerts else '',
            'Campaigns': ', '.join(sorted(account_campaigns.get(account_id, set()))) if has_alerts else '',
            'First Alert Date': min([a['event_datetime'] for a in alerts]) if alerts else '',
            'Last Alert Date': max([a['event_datetime'] for a in alerts]) if alerts else ''
        })
    
    # Create summary DataFrame
    summary_df = pd.DataFrame(report_data)
    
    # Create detailed alerts DataFrame
    detailed_alerts = []
    for account_id, alerts in account_alerts.items():
        for alert in alerts:
            detailed_alerts.append({
                'Account ID': account_id,
                **alert
            })
    
    detailed_df = pd.DataFrame(detailed_alerts) if detailed_alerts else pd.DataFrame()
    
    # Create alert types summary
    alert_type_summary = []
    for account_id in sorted(account_alerts.keys()):
        if account_id in account_alert_types:
            for alert_type, count in sorted(account_alert_types[account_id].items(), key=lambda x: -x[1]):
                alert_type_summary.append({
                    'Account ID': account_id,
                    'Alert Type': alert_type,
                    'Count': count
                })
    
    alert_types_df = pd.DataFrame(alert_type_summary) if alert_type_summary else pd.DataFrame()
    
    # Create threats summary (security URLs and threat categories)
    threats_data = []
    for account_id in sorted(account_threats.keys()):
        for threat in account_threats[account_id]:
            threats_data.append({
                'Account ID': account_id,
                'Alert ID': threat['alert_id'],
                'Project Name': threat['project_name'],
                'Campaign ID': threat['campaign_id'],
                'Alert Type': threat['alert_name'],
                'Event Date': threat['event_datetime'],
                'Threat Category': threat.get('threat_category', ''),
                'Has Security URLs': 'YES' if threat['has_security_urls'] else 'NO',
                'Security URL Count': threat.get('security_url_count', 0),
                'Security URLs (first 3)': threat.get('security_incident_urls', ''),
                'Alert Details URL': threat.get('alert_details_url', '')
            })
    
    threats_df = pd.DataFrame(threats_data) if threats_data else pd.DataFrame()
    
    # Save to Excel with multiple sheets
    output_file = f"account_alerts_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        if not detailed_df.empty:
            detailed_df.to_excel(writer, sheet_name='Detailed Alerts', index=False)
        
        if not alert_types_df.empty:
            alert_types_df.to_excel(writer, sheet_name='Alert Types by Account', index=False)
        
        if not threats_df.empty:
            threats_df.to_excel(writer, sheet_name='Threats Details', index=False)
        
        # Add statistics sheet
        stats_data = {
            'Metric': [
                'Total Accounts Checked',
                'Accounts with Alerts',
                'Accounts without Alerts',
                'Total Alerts Found',
                'Total Unique Projects',
                'Total Unique Campaigns',
                'Unique Alert Types',
                'Accounts with Threat Details',
                'Total Threat Alerts (with URLs/Categories)',
                'Date Range Start',
                'Date Range End'
            ],
            'Value': [
                len(account_ids),
                len(account_alerts),
                len(account_ids) - len(account_alerts),
                sum(len(alerts) for alerts in account_alerts.values()),
                len(set().union(*[account_projects.get(aid, set()) for aid in account_ids])),
                len(set().union(*[account_campaigns.get(aid, set()) for aid in account_ids])),
                len(set().union(*[set(account_alert_types.get(aid, {}).keys()) for aid in account_ids])),
                len(account_threats),
                sum(len(threats) for threats in account_threats.values()),
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            ]
        }
        stats_df = pd.DataFrame(stats_data)
        stats_df.to_excel(writer, sheet_name='Statistics', index=False)
    
    print(f"✅ Report saved to: {output_file}")
    
    # Print summary
    print(f"\n" + "="*60)
    print(f"📊 SUMMARY REPORT")
    print(f"="*60)
    print(f"Total Accounts Checked: {len(account_ids)}")
    print(f"Accounts WITH Alerts: {len(account_alerts)}")
    print(f"Accounts WITHOUT Alerts: {len(account_ids) - len(account_alerts)}")
    print(f"Total Alerts Found: {sum(len(alerts) for alerts in account_alerts.values())}")
    print(f"\n✅ Accounts WITH alerts in last 90 days:")
    for account_id in sorted(account_alerts.keys()):
        alerts = account_alerts[account_id]
        alert_types = account_alert_types[account_id]
        top_alert = max(alert_types.items(), key=lambda x: x[1]) if alert_types else ('Unknown', 0)
        print(f"  • Account {account_id}: {len(alerts)} alerts, {len(account_projects[account_id])} projects (Top: {top_alert[0]}={top_alert[1]})")
    
    if len(account_ids) > len(account_alerts):
        print(f"\n❌ Accounts WITHOUT alerts in last 90 days:")
        no_alerts = set(account_ids) - set(account_alerts.keys())
        for account_id in sorted(no_alerts):
            print(f"  • Account {account_id}: No alerts")
    
    print(f"\n📄 Detailed report saved to: {output_file}")
    print(f"="*60)


if __name__ == "__main__":
    main()
