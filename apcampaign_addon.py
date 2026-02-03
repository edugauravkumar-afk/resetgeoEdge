#!/usr/bin/env python3
"""
APcampaign Daily Monitor - Add to existing daily monitor system
Monitors APcampaign accounts and resets from 1,12 to 0,0 when inactive
"""

import os
import pandas as pd
import pymysql
import requests
import time
import logging
from datetime import datetime
from dotenv import load_dotenv

from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class APCampaignDailyMonitor:
    """APcampaign monitoring to add to existing daily monitor"""
    
    def __init__(self):
        # Database config
        self.db_config = {
            'host': os.getenv('MYSQL_HOST', 'proxysql-office.taboolasyndication.com'),
            'port': int(os.getenv('MYSQL_PORT', 6033)),
            'user': os.getenv('MYSQL_USER', 'gaurav.k'),
            'password': os.getenv('MYSQL_PASSWORD', 'Hare_1317'),
            'database': os.getenv('MYSQL_DB', 'trc'),
            'charset': 'utf8mb4'
        }
        
        self.api_key = os.getenv("GEOEDGE_API_KEY", "c60cd125b34b6333c8708e6478d1fb8e")
        self.base_url = "https://api.geoedge.com/rest/analytics/v3"
        
        # Stats tracking
        self.stats = {
            'total_projects_monitored': 0,
            'inactive_campaigns_found': 0,
            'projects_reset_to_0_0': 0,
            'successful_resets': 0,
            'failed_resets': 0,
            'inactive_projects_details': []
        }

    def get_apcampaign_projects(self):
        """Get APcampaign projects with account info using correct joins"""
        try:
            # Read campaign IDs from CSV
            df = pd.read_csv('LP_Alerts_24H/APcampaign.csv')
            campaign_ids = df['Campaign ID'].tolist()
            
            logger.info(f"📋 Found {len(campaign_ids)} campaigns in APcampaign.csv")
            
            conn = pymysql.connect(**self.db_config)
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            try:
                campaign_ids_str = ','.join(map(str, campaign_ids))
                
                cursor.execute(f"""
                    SELECT DISTINCT
                        gep.project_id,
                        gep.campaign_id,
                        gep.locations,
                        c.syndicator_id AS account_id,
                        pub.status AS account_status,
                        LC.display_status as campaign_status
                    FROM trc.geo_edge_projects AS gep
                    JOIN trc.sp_campaigns c ON gep.campaign_id = c.id
                    JOIN trc.publishers pub ON c.syndicator_id = pub.id
                    JOIN trc.sp_campaigns_latest_snapshot LC ON LC.id = c.id
                    WHERE gep.campaign_id IN ({campaign_ids_str})
                    ORDER BY gep.campaign_id
                """)
                
                results = cursor.fetchall()
                logger.info(f"🎯 Found {len(results)} APcampaign projects for monitoring")
                
                return results
                
            finally:
                cursor.close()
                conn.close()
                
        except Exception as e:
            logger.error(f"❌ Error getting APcampaign projects: {e}")
            return []

    def check_project_geoedge_config(self, project_id):
        """Check current GeoEdge configuration via API"""
        try:
            url = f"{self.base_url}/projects/{project_id}"
            headers = {"Authorization": self.api_key}
            
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                result = response.json()
                if 'response' in result and 'project' in result['response']:
                    project = result['response']['project']
                    return {
                        'auto_scan': int(project.get('auto_scan', 0)),
                        'times_per_day': int(project.get('times_per_day', 0)),
                        'success': True
                    }
            
            return {'auto_scan': 0, 'times_per_day': 0, 'success': False}
        except Exception as e:
            logger.error(f"❌ Error checking project {project_id}: {e}")
            return {'auto_scan': 0, 'times_per_day': 0, 'success': False}
    
    def reset_project_config(self, project_id):
        """Reset project to 0,0 configuration using the correct API format"""
        try:
            url = f"{self.base_url}/projects/{project_id}"
            headers = {"Authorization": self.api_key}
            
            # Only send auto_scan=0, don't send times_per_day when auto_scan is 0
            data = {"auto_scan": 0}
            
            logger.debug(f"Sending PUT to {url} with data: {data}")
            
            response = requests.put(url, headers=headers, data=data, timeout=30)
            logger.debug(f"API Response: {response.status_code} - {response.text[:200]}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    success = result.get('status', {}).get('code') == 'Success'
                    
                    if success:
                        logger.info(f"✅ API reset successful for {project_id[:16]}...")
                        
                        # Verify the change with a longer wait
                        time.sleep(3)  # Give more time for API processing
                        verification = self.check_project_geoedge_config(project_id)
                        
                        if verification['success'] and verification['auto_scan'] == 0:
                            logger.info(f"✅ Verification successful - {project_id[:16]}... now configured as {verification['auto_scan']},{verification['times_per_day']}")
                            return True
                        else:
                            logger.warning(f"⚠️ API reset succeeded but verification failed for {project_id[:16]}...")
                            logger.warning(f"   Expected: auto_scan=0, Got: ({verification['auto_scan']},{verification['times_per_day']})")
                            return False
                    else:
                        logger.error(f"❌ API returned success=False for {project_id[:16]}...")
                        logger.error(f"   Response: {result}")
                        return False
                        
                except ValueError as e:
                    logger.error(f"❌ Invalid JSON response for {project_id[:16]}...: {e}")
                    return False
            else:
                logger.error(f"❌ API call failed for {project_id[:16]}... - Status: {response.status_code}")
                logger.error(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Exception during reset for {project_id[:16]}...: {e}")
            return False
    
    def monitor_apcampaign_accounts(self):
        """Main monitoring function for APcampaign accounts (multithreaded)"""
        logger.info("🔍 Starting APcampaign daily monitoring...")
        projects = self.get_apcampaign_projects()
        if not projects:
            logger.warning("❌ No APcampaign projects found")
            return self.stats
        logger.info(f"🔍 Checking {len(projects)} APcampaign projects...")
        self.stats['total_projects_monitored'] = len(projects)

        def process_project(project):
            project_id = project['project_id']
            campaign_id = project['campaign_id']
            account_id = project.get('account_id')
            account_status = project.get('account_status', 'unknown')
            locations = project.get('locations', 'N/A')
            # Only check account status, not campaign status
            account_is_active = False
            if account_id:
                account_status_raw = account_status.lower() if account_status else 'unknown'
                account_is_active = account_status_raw in ['active', 'live']
            is_active = account_is_active
            if not is_active:
                inactive_reason = []
                if not account_is_active:
                    inactive_reason.append(f"account {account_id} is {account_status}")
                reason_text = " and ".join(inactive_reason)
                current_config = self.check_project_geoedge_config(project_id)
                if current_config['success']:
                    auto_scan = current_config['auto_scan']
                    times_per_day = current_config['times_per_day']
                    if auto_scan != 0:
                        reset_success = self.reset_project_config(project_id)
                        return {
                            'project_id': project_id,
                            'campaign_id': campaign_id,
                            'account_id': account_id,
                            'locations': locations,
                            'old_config': f"{auto_scan},{times_per_day}",
                            'new_config': "0,0" if reset_success else "failed",
                            'inactive_reason': reason_text,
                            'reset_success': reset_success
                        }, True, reset_success
                return None, True, False
            return None, False, False

        with ThreadPoolExecutor(max_workers=8) as executor:
            future_to_project = {executor.submit(process_project, project): project for project in projects}
            for i, future in enumerate(as_completed(future_to_project), 1):
                result, was_inactive, reset_success = future.result()
                if was_inactive:
                    self.stats['inactive_campaigns_found'] += 1
                if result:
                    self.stats['projects_reset_to_0_0'] += 1
                    if result['reset_success']:
                        self.stats['successful_resets'] += 1
                    else:
                        self.stats['failed_resets'] += 1
                    self.stats['inactive_projects_details'].append(result)
                if i % 100 == 0:
                    logger.info(f"   Progress: {i}/{len(projects)} projects checked...")

        logger.info("=" * 60)
        logger.info("📊 APcampaign Daily Monitoring Summary")
        logger.info("=" * 60)
        logger.info(f"Total projects monitored: {self.stats['total_projects_monitored']}")
        logger.info(f"Inactive accounts/campaigns found: {self.stats['inactive_campaigns_found']}")
        logger.info(f"Projects that needed reset: {self.stats['projects_reset_to_0_0']}")
        logger.info(f"Successful resets (1,12 → 0,0): {self.stats['successful_resets']}")
        logger.info(f"Failed resets (will retry): {self.stats['failed_resets']}")
        if self.stats['inactive_campaigns_found'] == 0:
            logger.info("🎉 All APcampaign accounts and campaigns remain active!")
        else:
            if self.stats['projects_reset_to_0_0'] > 0:
                success_rate = (self.stats['successful_resets'] / self.stats['projects_reset_to_0_0'] * 100)
                logger.info(f"📈 Reset success rate: {success_rate:.1f}%")
                if success_rate < 100:
                    logger.info(f"💡 Failed resets will be retried in next daily run")
            else:
                logger.info("ℹ️ All inactive projects were already configured as 0,0")
        return self.stats

def run_apcampaign_monitoring():
    """Function to be called from existing daily monitor"""
    monitor = APCampaignDailyMonitor()
    return monitor.monitor_apcampaign_accounts()

if __name__ == "__main__":
    # Standalone execution
    results = run_apcampaign_monitoring()
    print(f"\n🏁 APcampaign monitoring completed!")
    print(f"Check logs above for detailed results.")