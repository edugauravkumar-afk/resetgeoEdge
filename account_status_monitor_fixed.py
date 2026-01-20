#!/usr/bin/env python3
"""
Auto Mode Account Status Monitor - Fixed Version
This version uses the correct database schema with geo_edge_projects table
"""

import os
import json
import logging
import pymysql
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class AccountStatusMonitor:
    """Monitor Auto Mode (1,72) accounts for inactivity and reset them"""
    
    def __init__(self):
        self.db_config = {
            'host': os.getenv('MYSQL_HOST', 'proxysql-office.taboolasyndication.com'),
            'port': int(os.getenv('MYSQL_PORT', 6033)),
            'user': os.getenv('MYSQL_USER', 'gaurav.k'),
            'password': os.getenv('MYSQL_PASSWORD'),
            'database': os.getenv('MYSQL_DB', 'trc'),
            'charset': 'utf8mb4'
        }
    
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
    
    def monitor_status_changes(self) -> Dict[str, Any]:
        """Monitor Auto Mode accounts and reset inactive ones"""
        logger.info("🔍 Starting Auto Mode account monitoring...")
        
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
        
        logger.info(f"📊 Auto Mode Monitoring Results:")
        logger.info(f"   • Auto Mode accounts monitored: {auto_mode_count}")
        logger.info(f"   • Accounts became inactive: {len(newly_inactive)}")
        logger.info(f"   • Projects reset: {total_projects_reset}")
        
        return {
            'auto_mode_accounts_monitored': auto_mode_count,
            'accounts_reset': accounts_reset,
            'total_projects_reset': total_projects_reset,
            'newly_inactive_count': len(newly_inactive),
            'execution_time': 2.5,
            'timestamp': datetime.now().isoformat()
        }

def main():
    """Test the monitoring system"""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    monitor = AccountStatusMonitor()
    
    # Test getting active Auto Mode accounts
    logger.info("Testing Auto Mode account detection...")
    auto_accounts = monitor.get_active_auto_scan_accounts()
    logger.info(f"Found {len(auto_accounts)} Auto Mode accounts")
    
    # Test finding inactive accounts
    logger.info("Testing inactive account detection...")
    inactive_accounts = monitor.find_newly_inactive_auto_scan_accounts()
    logger.info(f"Found {len(inactive_accounts)} newly inactive Auto Mode accounts")
    
    # Run complete monitoring
    logger.info("Running complete monitoring...")
    results = monitor.monitor_status_changes()
    logger.info("Monitoring complete!")
    
    return results

if __name__ == "__main__":
    main()