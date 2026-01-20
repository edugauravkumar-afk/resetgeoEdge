#!/usr/bin/env python3
"""
Reset Auto Mode to Manual Mode for All Inactive Accounts
Update all projects under the 197 inactive accounts from (1,72) to (0,0)
"""

import logging
import pymysql
import requests
import time
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv
import os

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# GeoEdge API Configuration
API_KEY = os.getenv("GEOEDGE_API_KEY")
BASE_URL = "https://api.geoedge.com/rest/analytics/v3"
DELAY_BETWEEN_REQUESTS = 2  # 2 seconds delay between API calls

# All 197 inactive account IDs from our comprehensive analysis
INACTIVE_ACCOUNT_IDS = [
    1929079, 1920194, 1915600, 1919282, 1908683, 1425690, 1914250, 1912974, 1899760, 1907271,
    1934286, 1910198, 1929015, 1889326, 1905236, 1781411, 1896030, 1857143, 1352198, 1907383,
    1881854, 1886322, 1927367, 1925530, 1924955, 1899166, 1912802, 1928013, 1924961, 1895867,
    1881883, 1833285, 1424656, 1607160, 1882251, 1833860, 1925694, 1909385, 1909587, 1920469,
    1936885, 1894130, 1907516, 1896885, 1941905, 1894525, 1938059, 1933775, 1644506, 1901007,
    1907885, 1921462, 1929107, 1929951, 1935336, 1939790, 1943993, 1943664, 1943602, 1936843,
    1935145, 1935730, 1942405, 1842014, 1943621, 1911893, 1928843, 1939247, 1944607, 1945348,
    1883417, 1939334, 1944573, 1938066, 1925696, 1945942, 1945937, 1904245, 1947296, 1936827,
    1908837, 1947109, 1947304, 1920193, 1792854, 1904249, 1927093, 1943951, 1511236, 1860125,
    1942999, 1947765, 1947761, 1941156, 1920197, 1939816, 1920200, 1937426, 1934285, 1904243,
    1927073, 1939713, 1923392, 1946080, 1946084, 1927074, 1904248, 1925332, 1889788, 1941195,
    1941131, 1820428, 1945850, 1934283, 1924943, 1948754, 1951144, 1941669, 1940262, 1826503,
    1827872, 1943663, 1346317, 1916785, 1951979, 1933777, 1938564, 1939814, 1950370, 1939709,
    1941196, 1908656, 1833317, 1823078, 1861571, 1949239, 1890632, 1909654, 1904244, 1929315,
    1958866, 1940640, 1949134, 1833361, 1803836, 1859995, 1937588, 1929299, 1943081, 1949258,
    1957113, 1912972, 1949157, 1959374, 1823262, 1939712, 1939963, 1951366, 1948109, 1895912,
    1947177, 1766692, 1881443, 1948980, 1708395, 1777430, 1874381, 1936999, 1936044, 1923699,
    1897286, 1895857, 1958722, 1959226, 1959240, 1945580, 1894752, 1957360, 1942452, 1958388,
    1959729, 1956903, 1606199, 1958830, 1913854, 1950734, 1952057, 1958987, 1847119, 1894125,
    1952731, 1925532, 1872062, 1939729, 1671075, 1878208
]

class InactiveAccountResetter:
    """Reset inactive accounts from Auto Mode (1,72) to Manual Mode (0,0)"""
    
    def __init__(self):
        self.db_config = {
            'host': os.getenv('MYSQL_HOST', 'proxysql-office.taboolasyndication.com'),
            'port': int(os.getenv('MYSQL_PORT', 6033)),
            'user': os.getenv('MYSQL_USER', 'gaurav.k'),
            'password': os.getenv('MYSQL_PASSWORD'),
            'database': os.getenv('MYSQL_DB', 'trc'),
            'charset': 'utf8mb4'
        }
        
        self.successful_resets = 0
        self.failed_resets = 0
        self.total_projects = 0
        self.reset_details = []
    
    def _get_db_connection(self):
        """Create database connection"""
        return pymysql.connect(**self.db_config)
    
    def get_projects_for_inactive_accounts(self):
        """Get all projects for the 197 inactive accounts"""
        db = self._get_db_connection()
        cursor = db.cursor(pymysql.cursors.DictCursor)
        
        try:
            print("🔍 FINDING PROJECTS FOR 197 INACTIVE ACCOUNTS:")
            print("=" * 60)
            
            placeholders = ','.join(['%s'] * len(INACTIVE_ACCOUNT_IDS))
            
            sql = f"""
                SELECT DISTINCT
                    gep.project_id,
                    gep.campaign_id,
                    sc.syndicator_id as account_id,
                    p.name as publisher_name,
                    p.status as account_status,
                    gep.locations,
                    gep.creation_date
                FROM trc.geo_edge_projects AS gep
                JOIN trc.sp_campaigns sc ON gep.campaign_id = sc.id
                JOIN trc.publishers p ON sc.syndicator_id = p.id
                WHERE sc.syndicator_id IN ({placeholders})
                  AND p.status = 'INACTIVE'
                ORDER BY sc.syndicator_id, gep.project_id
            """
            
            cursor.execute(sql, INACTIVE_ACCOUNT_IDS)
            results = cursor.fetchall()
            
            print(f"📊 Found {len(results)} projects across {len(set(r['account_id'] for r in results))} inactive accounts")
            print()
            
            # Group projects by account for summary
            projects_by_account = {}
            for result in results:
                account_id = result['account_id']
                if account_id not in projects_by_account:
                    projects_by_account[account_id] = {
                        'publisher_name': result['publisher_name'],
                        'account_status': result['account_status'],
                        'projects': []
                    }
                projects_by_account[account_id]['projects'].append(result)
            
            print(f"📋 ACCOUNT BREAKDOWN:")
            for account_id, data in list(projects_by_account.items())[:10]:  # Show first 10
                print(f"   Account {account_id}: {len(data['projects'])} projects - {data['publisher_name']}")
            
            if len(projects_by_account) > 10:
                print(f"   ... and {len(projects_by_account) - 10} more accounts")
            
            print()
            return results
            
        except Exception as e:
            logger.error(f"Error getting projects: {e}")
            return []
        finally:
            cursor.close()
            db.close()
    
    def update_project_to_manual_mode(self, project_id: str) -> Dict[str, Any]:
        """Update a single project from Auto Mode (1,72) to Manual Mode (0,0)"""
        url = f"{BASE_URL}/projects/{project_id}"
        headers = {"Authorization": API_KEY}
        # When auto_scan=0, don't send times_per_day to avoid API conflict
        data = {
            "auto_scan": 0
        }
        
        try:
            response = requests.put(url, headers=headers, data=data, timeout=60)
            response.raise_for_status()
            result = response.json()
            
            if result.get('status', {}).get('code') == 'Success':
                return {'success': True, 'project_id': project_id}
            else:
                return {'success': False, 'project_id': project_id, 'error': f"API returned: {result}"}
                
        except Exception as e:
            return {'success': False, 'project_id': project_id, 'error': str(e)}
    
    def reset_all_inactive_projects(self, projects: List[Dict[str, Any]]):
        """Reset all projects for inactive accounts to Manual Mode"""
        print("🔄 STARTING BULK RESET TO MANUAL MODE (0,0):")
        print("=" * 60)
        
        self.total_projects = len(projects)
        
        print(f"📊 RESET OPERATION DETAILS:")
        print(f"   • Total projects to reset: {self.total_projects}")
        print(f"   • From configuration: Auto Mode (1,72)")
        print(f"   • To configuration: Manual Mode (0,0)")
        print(f"   • API delay between requests: {DELAY_BETWEEN_REQUESTS} seconds")
        print()
        
        # Confirm operation
        confirm = input("🚨 This will reset ALL projects to Manual Mode. Continue? (yes/no): ")
        if confirm.lower() not in ['yes', 'y']:
            print("❌ Operation cancelled by user")
            return
        
        print("🚀 Starting reset operation...")
        print()
        
        start_time = datetime.now()
        
        for i, project in enumerate(projects, 1):
            project_id = project['project_id']
            account_id = project['account_id']
            publisher_name = project['publisher_name']
            
            print(f"[{i}/{self.total_projects}] Resetting project {project_id} (Account: {account_id})")
            
            # Update project via API
            result = self.update_project_to_manual_mode(project_id)
            
            if result['success']:
                self.successful_resets += 1
                print(f"   ✅ SUCCESS: {project_id} → Manual Mode (0,0)")
                self.reset_details.append({
                    'project_id': project_id,
                    'account_id': account_id,
                    'publisher_name': publisher_name,
                    'status': 'SUCCESS',
                    'timestamp': datetime.now()
                })
            else:
                self.failed_resets += 1
                print(f"   ❌ FAILED: {project_id} → {result['error']}")
                self.reset_details.append({
                    'project_id': project_id,
                    'account_id': account_id,
                    'publisher_name': publisher_name,
                    'status': 'FAILED',
                    'error': result['error'],
                    'timestamp': datetime.now()
                })
            
            # Progress update every 50 projects
            if i % 50 == 0:
                elapsed = datetime.now() - start_time
                success_rate = (self.successful_resets / i) * 100
                print(f"   📊 Progress: {i}/{self.total_projects} ({success_rate:.1f}% success rate, elapsed: {elapsed})")
                print()
            
            # Delay between requests to avoid overwhelming the API
            time.sleep(DELAY_BETWEEN_REQUESTS)
        
        end_time = datetime.now()
        total_time = end_time - start_time
        
        print()
        print("🎯 RESET OPERATION COMPLETE!")
        print("=" * 60)
        print(f"📊 FINAL SUMMARY:")
        print(f"   • Total projects processed: {self.total_projects}")
        print(f"   • Successful resets: {self.successful_resets}")
        print(f"   • Failed resets: {self.failed_resets}")
        print(f"   • Success rate: {(self.successful_resets/self.total_projects*100):.1f}%")
        print(f"   • Total time: {total_time}")
        print()
        
        if self.failed_resets > 0:
            print("❌ FAILED RESETS:")
            failed_details = [d for d in self.reset_details if d['status'] == 'FAILED']
            for detail in failed_details[:10]:  # Show first 10 failures
                print(f"   Project {detail['project_id']} (Account {detail['account_id']}): {detail['error']}")
            if len(failed_details) > 10:
                print(f"   ... and {len(failed_details) - 10} more failures")
            print()
        
        print("✅ All inactive accounts' projects have been processed!")
        print("✅ These accounts are now set to Manual Mode (0,0)")
    
    def generate_reset_report(self):
        """Generate a detailed report of the reset operation"""
        report_filename = f"inactive_accounts_reset_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(report_filename, 'w') as f:
            f.write("INACTIVE ACCOUNTS RESET REPORT\n")
            f.write("=" * 50 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Projects: {self.total_projects}\n")
            f.write(f"Successful Resets: {self.successful_resets}\n")
            f.write(f"Failed Resets: {self.failed_resets}\n")
            f.write(f"Success Rate: {(self.successful_resets/self.total_projects*100):.1f}%\n")
            f.write("\n")
            
            f.write("DETAILED RESULTS:\n")
            f.write("-" * 30 + "\n")
            for detail in self.reset_details:
                f.write(f"Project: {detail['project_id']} | Account: {detail['account_id']} | ")
                f.write(f"Status: {detail['status']} | Time: {detail['timestamp']}\n")
                if detail['status'] == 'FAILED':
                    f.write(f"  Error: {detail['error']}\n")
        
        print(f"📄 Detailed report saved to: {report_filename}")

def main():
    """Main function to reset all inactive accounts to Manual Mode"""
    print("🔄 RESET INACTIVE ACCOUNTS TO MANUAL MODE")
    print("=" * 70)
    print("Resetting all projects under 197 inactive accounts from (1,72) to (0,0)")
    print()
    
    resetter = InactiveAccountResetter()
    
    # Get all projects for inactive accounts
    projects = resetter.get_projects_for_inactive_accounts()
    
    if not projects:
        print("❌ No projects found for inactive accounts")
        return
    
    # Reset all projects to Manual Mode
    resetter.reset_all_inactive_projects(projects)
    
    # Generate detailed report
    resetter.generate_reset_report()

if __name__ == "__main__":
    main()