#!/usr/bin/env python3
"""
Auto Mode Account Status Monitor - Fixed Version
This version uses the correct database schema with geo_edge_projects table
Now also monitors APcampaign accounts (1,12 to 0,0) and APNews status
"""

import os
import json
import logging
import pymysql
import pandas as pd
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
from dotenv import load_dotenv
from apcampaign_addon import run_apcampaign_monitoring

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class AccountStatusMonitor:
    """Monitor Auto Mode (1,72) accounts for inactivity and reset them + APcampaign (1,12) monitoring + APNews status"""
    
    def __init__(self):
        self.db_config = {
            'host': os.getenv('MYSQL_HOST', 'proxysql-office.taboolasyndication.com'),
            'port': int(os.getenv('MYSQL_PORT', 6033)),
            'user': os.getenv('MYSQL_USER', 'gaurav.k'),
            'password': os.getenv('MYSQL_PASSWORD'),
            'database': os.getenv('MYSQL_DB', 'trc'),
            'charset': 'utf8mb4'
        }
        
        # GeoEdge API configuration for APcampaign monitoring
        self.api_key = os.getenv("GEOEDGE_API_KEY", "c60cd125b34b6333c8708e6478d1fb8e")
        self.base_url = "https://api.geoedge.com/rest/analytics/v3"
    
    def _get_db_connection(self):
        """Create database connection"""
        return pymysql.connect(**self.db_config)
    
    def get_active_auto_scan_accounts(self) -> List[Dict]:
        """Get all accounts that currently have Auto Mode (1,72) configuration"""
        db = self._get_db_connection()
        cursor = db.cursor(pymysql.cursors.DictCursor)
        
        try:
            cursor.execute("""
                SELECT DISTINCT 
                    p.syndicator_id as id,
                    p.name,
                    p.status,
                    COUNT(DISTINCT gep.project_id) as project_count
                FROM publishers p
                INNER JOIN geo_edge_projects gep ON p.syndicator_id = gep.syndicator_id
                WHERE gep.auto_scan = 1 
                AND gep.times_per_day = 72
                AND p.status = 'active'
                GROUP BY p.syndicator_id, p.name, p.status
                ORDER BY project_count DESC
            """)
            
            results = cursor.fetchall()
            logger.info(f"Found {len(results)} active accounts with Auto Mode (1,72) configuration")
            return results
            
        except Exception as e:
            logger.error(f"Error getting active Auto Mode accounts: {e}")
            return []
        finally:
            cursor.close()
            db.close()
    
    def find_newly_inactive_auto_scan_accounts(self) -> List[Dict]:
        """Find Auto Mode accounts that became inactive in the last 24 hours"""
        db = self._get_db_connection()
        cursor = db.cursor(pymysql.cursors.DictCursor)
        
        try:
            cursor.execute("""
                SELECT DISTINCT
                    p.syndicator_id as id,
                    p.name,
                    p.status,
                    p.update_time,
                    COUNT(DISTINCT gep.project_id) as project_count
                FROM publishers p
                INNER JOIN geo_edge_projects gep ON p.syndicator_id = gep.syndicator_id
                WHERE p.status IN ('inactive', 'paused', 'suspended', 'frozen')
                AND p.update_time >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
                AND gep.auto_scan = 1
                AND gep.times_per_day = 72
                GROUP BY p.syndicator_id, p.name, p.status, p.update_time
                HAVING project_count > 0
                ORDER BY p.update_time DESC
            """)
            
            results = cursor.fetchall()
            logger.info(f"Found {len(results)} Auto Mode accounts that became inactive in last 24 hours")
            return results
            
        except Exception as e:
            logger.error(f"Error finding newly inactive Auto Mode accounts: {e}")
            return []
        finally:
            cursor.close()
            db.close()
    
    def reset_projects_to_manual_mode(self, account_id: int) -> int:
        """Reset all Auto Mode projects for an account to Manual Mode (0,0)"""
        db = self._get_db_connection()
        cursor = db.cursor()
        
        try:
            # Update geo_edge_projects from (1,72) to (0,0)
            cursor.execute("""
                UPDATE geo_edge_projects 
                SET auto_scan = 0, times_per_day = 0
                WHERE syndicator_id = %s 
                AND auto_scan = 1 
                AND times_per_day = 72
            """, (account_id,))
            
            projects_reset = cursor.rowcount
            db.commit()
            
            if projects_reset > 0:
                logger.info(f"✅ Reset {projects_reset} projects for account {account_id} from (1,72) to (0,0)")
            
            return projects_reset
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Failed to reset projects for account {account_id}: {e}")
            return 0
        finally:
            cursor.close()
            db.close()

    def get_apnews_account_statuses(self) -> Dict[str, Any]:
        """Get APNews account statuses from APNews.csv (including last 24h)"""
        try:
            df = pd.read_csv('APNews.csv')
            if 'IDs' in df.columns:
                account_ids = df['IDs'].dropna().astype(int).tolist()
            else:
                account_ids = df.iloc[:, 0].dropna().astype(int).tolist()

            if not account_ids:
                return {
                    'apnews_accounts_monitored': 0,
                    'apnews_inactive_count': 0,
                    'apnews_inactive_accounts': [],
                    'apnews_unknown_count': 0
                }

            db = self._get_db_connection()
            cursor = db.cursor(pymysql.cursors.DictCursor)

            try:
                placeholders = ','.join(['%s'] * len(account_ids))
                cursor.execute(f"""
                    SELECT id, name, status
                    FROM trc.publishers
                    WHERE id IN ({placeholders})
                """, account_ids)

                results = cursor.fetchall()
            finally:
                cursor.close()
                db.close()

            status_map = {row['id']: row for row in results}
            inactive_statuses = {'inactive', 'paused', 'suspended', 'frozen'}
            cutoff_time = datetime.now() - timedelta(hours=24)

            inactive_accounts = []
            newly_inactive_accounts = []
            unknown_accounts = 0

            for account_id in account_ids:
                info = status_map.get(account_id)
                if not info:
                    unknown_accounts += 1
                    continue

                status = (info.get('status') or '').lower()
                if status in inactive_statuses:
                    account_entry = {
                        'account_id': str(info.get('id')),
                        'account_name': info.get('name'),
                        'status': info.get('status')
                    }
                    inactive_accounts.append(account_entry)

                    update_time = info.get('update_time')
                    if update_time and update_time >= cutoff_time:
                        newly_inactive_accounts.append(account_entry)

            return {
                'apnews_accounts_monitored': len(account_ids),
                'apnews_inactive_count': len(inactive_accounts),
                'apnews_newly_inactive_count': len(newly_inactive_accounts),
                'apnews_newly_inactive_accounts': newly_inactive_accounts,
                'apnews_inactive_accounts': inactive_accounts,
                'apnews_unknown_count': unknown_accounts
            }

        except Exception as e:
            logger.error(f"❌ Error getting APNews account statuses: {e}")
            return {
                'apnews_accounts_monitored': 0,
                'apnews_inactive_count': 0,
                'apnews_newly_inactive_count': 0,
                'apnews_newly_inactive_accounts': [],
                'apnews_inactive_accounts': [],
                'apnews_unknown_count': 0
            }
    
    def get_apcampaign_project_mapping(self):
        """Get project IDs for campaigns from APcampaign.csv"""
        try:
            # Read campaign IDs
            df = pd.read_csv('LP_Alerts_24H/APcampaign.csv')
            campaign_ids = df['Campaign ID'].tolist()
            
            logger.info(f"📋 Found {len(campaign_ids)} campaigns in APcampaign.csv")
            
            # Database connection
            db = self._get_db_connection()
            cursor = db.cursor(pymysql.cursors.DictCursor)
            
            try:
                campaign_ids_str = ','.join(map(str, campaign_ids))
                
                cursor.execute(f"""
                    SELECT DISTINCT
                        p.project_id,
                        p.campaign_id,
                        p.locations,
                        p.syndicator_id AS account_id,
                        pub.status AS account_status,
                        sii.instruction_status
                    FROM trc.geo_edge_projects AS p
                    JOIN trc.sp_campaign_inventory_instructions sii ON p.campaign_id = sii.campaign_id
                    JOIN trc.publishers pub ON p.syndicator_id = pub.syndicator_id
                    WHERE p.campaign_id IN ({campaign_ids_str})
                    ORDER BY p.campaign_id
                """)
                
                results = cursor.fetchall()
                logger.info(f"🎯 Found {len(results)} APcampaign projects for monitoring")
                
                return results
                
            finally:
                cursor.close()
                db.close()
                
        except Exception as e:
            logger.error(f"❌ Error getting APcampaign project mapping: {e}")
            return []

    def check_campaign_status(self, campaign_id):
        """Check if campaign is active or inactive"""
        db = self._get_db_connection()
        cursor = db.cursor(pymysql.cursors.DictCursor)
        
        try:
            cursor.execute("""
                SELECT instruction_status
                FROM trc.sp_campaign_inventory_instructions
                WHERE campaign_id = %s
            """, (campaign_id,))
            
            result = cursor.fetchone()
            
            if result:
                return result['instruction_status'] == 'ACTIVE'
            else:
                return False  # If no record found, consider inactive
                
        except Exception as e:
            logger.error(f"❌ Error checking campaign {campaign_id} status: {e}")
            return False
        finally:
            cursor.close()
            db.close()

    def get_project_config(self, project_id):
        """Get current GeoEdge project configuration via API"""
        try:
            url = f"{self.base_url}/projects/{project_id}"
            headers = {"Authorization": self.api_key}
            
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                result = response.json()
                if 'response' in result and 'project' in result['response']:
                    project = result['response']['project']
                    
                    auto_scan = int(project.get('auto_scan', 0))
                    times_per_day = int(project.get('times_per_day', 0))
                    
                    return {
                        'auto_scan': auto_scan,
                        'times_per_day': times_per_day,
                        'success': True
                    }
            
            return {'auto_scan': 0, 'times_per_day': 0, 'success': False}
        except Exception as e:
            logger.error(f"❌ Error checking project {project_id}: {e}")
            return {'auto_scan': 0, 'times_per_day': 0, 'success': False}

    def reset_apcampaign_project_to_inactive(self, project_id):
        """Reset APcampaign project configuration to 0,0 (inactive)"""
        try:
            url = f"{self.base_url}/projects/{project_id}"
            headers = {"Authorization": self.api_key}
            
            # Set to inactive config (API rejects times_per_day when auto_scan=0)
            data = {"auto_scan": 0}
            
            response = requests.put(url, headers=headers, data=data, timeout=30)
            if response.status_code == 200:
                result = response.json()
                success = result.get('status', {}).get('code') == 'Success'
                
                if success:
                    # Verify the change
                    time.sleep(1)
                    verification = self.get_project_config(project_id)
                    if verification['success'] and verification['auto_scan'] == 0 and verification['times_per_day'] == 0:
                        return True
                    else:
                        logger.warning(f"⚠️ APcampaign reset sent but verification failed for {project_id}")
                        return False
                
            return False
        except Exception as e:
            logger.error(f"❌ Error resetting APcampaign project {project_id}: {e}")
            return False

    def monitor_apcampaign_accounts(self) -> Dict[str, Any]:
        """Monitor APcampaign accounts and reset inactive ones from 1,12 to 0,0"""
        logger.info("🔍 Starting APcampaign account monitoring...")
        
        # Get campaign-project mapping
        projects = self.get_apcampaign_project_mapping()
        
        if not projects:
            logger.warning("❌ No APcampaign projects found for monitoring")
            return {
                'apcampaign_projects_monitored': 0,
                'apcampaign_accounts_reset': [],
                'apcampaign_projects_reset': 0,
                'apcampaign_newly_inactive_count': 0
            }
        
        inactive_projects = []
        apcampaign_projects_reset = 0
        apcampaign_reset_success = 0
        apcampaign_reset_failures = 0
        
        logger.info(f"🔍 Checking {len(projects)} APcampaign projects...")
        
        for project in projects:
            project_id = project['project_id']
            campaign_id = project['campaign_id']
            locations = project.get('locations', 'N/A')
            account_id = project.get('account_id')
            account_status = (project.get('account_status') or '').lower()
            
            # Check if account or campaign is inactive
            is_campaign_active = self.check_campaign_status(campaign_id)
            is_account_inactive = account_status in ('inactive', 'paused', 'suspended', 'frozen')
            
            if (not is_campaign_active) or is_account_inactive:
                reason = "campaign inactive" if not is_campaign_active else "account inactive"
                logger.info(
                    f"⚠️ APcampaign {campaign_id} (acct {account_id}) is INACTIVE ({reason}) - checking GeoEdge config..."
                )
                
                # Check current GeoEdge configuration
                current_config = self.get_project_config(project_id)
                
                if current_config['success']:
                    auto_scan = current_config['auto_scan']
                    times_per_day = current_config['times_per_day']
                    
                    # If not already 0,0, reset it
                    if auto_scan != 0 or times_per_day != 0:
                        apcampaign_projects_reset += 1
                        logger.info(f"🔧 APcampaign resetting project {project_id[:16]}... from {auto_scan},{times_per_day} to 0,0...")
                        
                        if self.reset_apcampaign_project_to_inactive(project_id):
                            apcampaign_reset_success += 1
                            logger.info(f"✅ APcampaign successfully reset {project_id[:16]}... to 0,0")
                            
                            inactive_projects.append({
                                'project_id': project_id,
                                'campaign_id': campaign_id,
                                'locations': locations,
                                'reset_success': True,
                                'old_config': f"{auto_scan},{times_per_day}",
                                'new_config': "0,0"
                            })
                        else:
                            apcampaign_reset_failures += 1
                            logger.error(f"❌ APcampaign failed to reset {project_id[:16]}...")
                            
                            inactive_projects.append({
                                'project_id': project_id,
                                'campaign_id': campaign_id,
                                'locations': locations,
                                'reset_success': False,
                                'old_config': f"{auto_scan},{times_per_day}",
                                'new_config': "failed"
                            })
                    else:
                        logger.info(f"ℹ️ APcampaign project {project_id[:16]}... already configured as 0,0")
                else:
                    logger.error(f"❌ Could not check APcampaign GeoEdge config for {project_id[:16]}...")
            
            time.sleep(0.2)  # Small delay between checks
        
        logger.info(f"📊 APcampaign Monitoring Results:")
        logger.info(f"   • APcampaign projects monitored: {len(projects)}")
        logger.info(f"   • APcampaign accounts became inactive: {len(inactive_projects)}")
        logger.info(f"   • APcampaign projects reset: {apcampaign_projects_reset}")
        logger.info(f"   • APcampaign successful resets: {apcampaign_reset_success}")
        logger.info(f"   • APcampaign failed resets: {apcampaign_reset_failures}")
        
        return {
            'apcampaign_projects_monitored': len(projects),
            'apcampaign_accounts_reset': inactive_projects,
            'apcampaign_projects_reset': apcampaign_projects_reset,
            'apcampaign_newly_inactive_count': len(inactive_projects),
            'apcampaign_reset_success': apcampaign_reset_success,
            'apcampaign_reset_failures': apcampaign_reset_failures,
            'timestamp': datetime.now().isoformat()
        }
    
    def monitor_status_changes(self) -> Dict[str, Any]:
        """Monitor Auto Mode accounts (1,72 to 0,0) and APcampaign accounts (1,12 to 0,0) and reset inactive ones"""
        logger.info("🔍 Starting comprehensive account monitoring...")
        logger.info("=" * 60)
        
        # 1. Monitor Auto Mode accounts (1,72)
        logger.info("🎯 PHASE 1: Auto Mode (1,72) Account Monitoring")
        logger.info("-" * 40)
        
        # Get all active Auto Mode accounts
        auto_mode_accounts = self.get_active_auto_scan_accounts()
        auto_mode_count = len(auto_mode_accounts)
        
        # Find accounts that became inactive in last 24 hours
        newly_inactive = self.find_newly_inactive_auto_scan_accounts()
        
        # Reset projects for newly inactive accounts
        accounts_reset = []
        total_projects_reset = 0
        
        for account in newly_inactive:
            account_id = account['id']
            projects_reset = self.reset_projects_to_manual_mode(account_id)
            
            if projects_reset > 0:
                account_reset_data = {
                    'account_id': str(account_id),
                    'account_name': account['name'],
                    'status': 'PRIORITY_NEWLY_INACTIVE',
                    'auto_scan': 0,  # Now set to manual
                    'scans_per_day': 0,  # Now set to manual
                    'total_projects': account['project_count'],
                    'projects_reset': projects_reset,
                    'timestamp': datetime.now().isoformat()
                }
                accounts_reset.append(account_reset_data)
                total_projects_reset += projects_reset
        
        logger.info(f"📊 Auto Mode (1,72) Monitoring Results:")
        logger.info(f"   • Auto Mode accounts monitored: {auto_mode_count}")
        logger.info(f"   • Accounts became inactive: {len(newly_inactive)}")
        logger.info(f"   • Projects reset: {total_projects_reset}")
        
        # 2. Monitor APcampaign accounts (1,12) using addon
        logger.info("\n🎯 PHASE 2: APcampaign (1,12) Account Monitoring")
        logger.info("-" * 40)
        
        try:
            apcampaign_stats = run_apcampaign_monitoring()
            
            # Convert addon stats to match expected format
            apcampaign_results = {
                'apcampaign_projects_monitored': apcampaign_stats.get('total_projects_monitored', 0),
                'apcampaign_accounts_reset': apcampaign_stats.get('inactive_projects_details', []),
                'apcampaign_projects_reset': apcampaign_stats.get('projects_reset_to_0_0', 0),
                'apcampaign_newly_inactive_count': apcampaign_stats.get('inactive_campaigns_found', 0),
                'apcampaign_reset_success': apcampaign_stats.get('successful_resets', 0),
                'apcampaign_reset_failures': apcampaign_stats.get('failed_resets', 0),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"❌ APcampaign monitoring failed: {e}")
            apcampaign_results = {
                'apcampaign_projects_monitored': 0,
                'apcampaign_accounts_reset': [],
                'apcampaign_projects_reset': 0,
                'apcampaign_newly_inactive_count': 0,
                'apcampaign_reset_success': 0,
                'apcampaign_reset_failures': 0,
                'timestamp': datetime.now().isoformat()
            }

        # 3. APNews account status summary
        logger.info("\n🎯 PHASE 3: APNews Account Status Summary")
        logger.info("-" * 40)
        apnews_results = self.get_apnews_account_statuses()
        logger.info(f"APNews accounts monitored: {apnews_results.get('apnews_accounts_monitored', 0)}")
        logger.info(f"APNews inactive accounts (total): {apnews_results.get('apnews_inactive_count', 0)}")
        logger.info(f"APNews became inactive (last 24h): {apnews_results.get('apnews_newly_inactive_count', 0)}")
        logger.info(f"APNews unknown accounts: {apnews_results.get('apnews_unknown_count', 0)}")
        
        # Combine results
        combined_results = {
            # Auto Mode (1,72) results
            'auto_mode_accounts_monitored': auto_mode_count,
            'accounts_reset': accounts_reset,
            'total_projects_reset': total_projects_reset,
            'newly_inactive_count': len(newly_inactive),
            
            # APcampaign (1,12) results
            'apcampaign_projects_monitored': apcampaign_results.get('apcampaign_projects_monitored', 0),
            'apcampaign_accounts_reset': apcampaign_results.get('apcampaign_accounts_reset', []),
            'apcampaign_projects_reset': apcampaign_results.get('apcampaign_projects_reset', 0),
            'apcampaign_newly_inactive_count': apcampaign_results.get('apcampaign_newly_inactive_count', 0),
            'apcampaign_reset_success': apcampaign_results.get('apcampaign_reset_success', 0),
            'apcampaign_reset_failures': apcampaign_results.get('apcampaign_reset_failures', 0),

            # APNews account status results
            'apnews_accounts_monitored': apnews_results.get('apnews_accounts_monitored', 0),
            'apnews_inactive_count': apnews_results.get('apnews_inactive_count', 0),
            'apnews_newly_inactive_count': apnews_results.get('apnews_newly_inactive_count', 0),
            'apnews_newly_inactive_accounts': apnews_results.get('apnews_newly_inactive_accounts', []),
            'apnews_inactive_accounts': apnews_results.get('apnews_inactive_accounts', []),
            'apnews_unknown_count': apnews_results.get('apnews_unknown_count', 0),
            
            # Combined totals
            'total_accounts_monitored': auto_mode_count + apcampaign_results.get('apcampaign_projects_monitored', 0),
            'total_inactive_found': len(newly_inactive) + apcampaign_results.get('apcampaign_newly_inactive_count', 0),
            'total_all_projects_reset': total_projects_reset + apcampaign_results.get('apcampaign_projects_reset', 0),
            
            'execution_time': 5.0,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info("\n" + "=" * 60)
        logger.info("📊 COMPREHENSIVE MONITORING SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Auto Mode (1,72) accounts monitored: {auto_mode_count}")
        logger.info(f"Auto Mode accounts became inactive: {len(newly_inactive)}")
        logger.info(f"Auto Mode projects reset: {total_projects_reset}")
        logger.info(f"APcampaign projects monitored: {apcampaign_results.get('apcampaign_projects_monitored', 0)}")
        logger.info(f"APcampaign accounts became inactive: {apcampaign_results.get('apcampaign_newly_inactive_count', 0)}")
        logger.info(f"APcampaign projects reset: {apcampaign_results.get('apcampaign_projects_reset', 0)}")
        logger.info(f"APNews accounts monitored: {apnews_results.get('apnews_accounts_monitored', 0)}")
        logger.info(f"APNews inactive accounts: {apnews_results.get('apnews_inactive_count', 0)}")
        logger.info(f"APNews unknown accounts: {apnews_results.get('apnews_unknown_count', 0)}")
        logger.info(f"TOTAL inactive accounts found: {combined_results['total_inactive_found']}")
        logger.info(f"TOTAL projects reset: {combined_results['total_all_projects_reset']}")
        
        return combined_results

def main():
    """Test the comprehensive monitoring system"""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    monitor = AccountStatusMonitor()
    
    # Test getting active Auto Mode accounts
    logger.info("Testing Auto Mode (1,72) account detection...")
    auto_accounts = monitor.get_active_auto_scan_accounts()
    logger.info(f"Found {len(auto_accounts)} Auto Mode accounts")
    
    # Test finding inactive accounts
    logger.info("Testing inactive Auto Mode account detection...")
    inactive_accounts = monitor.find_newly_inactive_auto_scan_accounts()
    logger.info(f"Found {len(inactive_accounts)} newly inactive Auto Mode accounts")
    
    # Test APcampaign project mapping
    logger.info("Testing APcampaign project mapping...")
    apcampaign_projects = monitor.get_apcampaign_project_mapping()
    logger.info(f"Found {len(apcampaign_projects)} APcampaign projects")
    
    # Run complete comprehensive monitoring
    logger.info("Running comprehensive monitoring (Auto Mode + APcampaign)...")
    results = monitor.monitor_status_changes()
    logger.info("Comprehensive monitoring complete!")
    
    return results

if __name__ == "__main__":
    main()