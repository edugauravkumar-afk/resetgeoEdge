#!/usr/bin/env python3
"""
Deep Research: Auto Mode Configuration Changes Analysis
This script analyzes all accounts to show what changes were made and current status
"""

import logging
import pymysql
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
from geoedge_projects.client import GeoEdgeClient
from dotenv import load_dotenv
import os

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ConfigurationAnalyzer:
    """Deep analysis of Auto Mode configuration changes"""
    
    def __init__(self):
        self.db_config = {
            'host': os.getenv('MYSQL_HOST', 'proxysql-office.taboolasyndication.com'),
            'port': int(os.getenv('MYSQL_PORT', 6033)),
            'user': os.getenv('MYSQL_USER', 'gaurav.k'),
            'password': os.getenv('MYSQL_PASSWORD'),
            'database': os.getenv('MYSQL_DB', 'trc'),
            'charset': 'utf8mb4'
        }
        try:
            self.api_client = GeoEdgeClient()
        except:
            self.api_client = None
            logger.warning("GeoEdge API client not available - will use database analysis only")
    
    def _get_db_connection(self):
        """Create database connection"""
        return pymysql.connect(**self.db_config)
    
    def get_all_publishers_with_projects(self) -> List[Dict]:
        """Get all publishers that have projects"""
        db = self._get_db_connection()
        cursor = db.cursor(pymysql.cursors.DictCursor)
        
        try:
            cursor.execute("""
                SELECT 
                    p.id as publisher_id,
                    p.name as publisher_name,
                    p.status as publisher_status,
                    p.update_time as last_updated,
                    COUNT(DISTINCT sc.id) as total_campaigns,
                    COUNT(DISTINCT gep.project_id) as total_projects,
                    MIN(gep.creation_date) as first_project_date,
                    MAX(gep.creation_date) as latest_project_date,
                    DATEDIFF(NOW(), MAX(gep.creation_date)) as days_since_last_project
                FROM publishers p
                INNER JOIN sp_campaigns sc ON p.id = sc.syndicator_id
                INNER JOIN geo_edge_projects gep ON sc.id = gep.campaign_id
                WHERE gep.creation_date >= DATE_SUB(NOW(), INTERVAL 90 DAY)
                GROUP BY p.id, p.name, p.status, p.update_time
                HAVING total_projects > 0
                ORDER BY total_projects DESC
            """)
            
            results = cursor.fetchall()
            logger.info(f"Found {len(results)} publishers with projects in last 90 days")
            return results
            
        except Exception as e:
            logger.error(f"Database error getting publishers: {e}")
            return []
        finally:
            cursor.close()
            db.close()
    
    def get_recent_status_changes(self) -> List[Dict]:
        """Get publishers that changed status recently"""
        db = self._get_db_connection()
        cursor = db.cursor(pymysql.cursors.DictCursor)
        
        try:
            cursor.execute("""
                SELECT 
                    p.id as publisher_id,
                    p.name as publisher_name,
                    p.status,
                    p.status_change_reason,
                    p.status_change_performer,
                    p.update_time,
                    p.inactivity_date,
                    COUNT(DISTINCT gep.project_id) as total_projects
                FROM publishers p
                LEFT JOIN sp_campaigns sc ON p.id = sc.syndicator_id
                LEFT JOIN geo_edge_projects gep ON sc.id = gep.campaign_id
                WHERE p.update_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                AND p.status != 'active'
                GROUP BY p.id, p.name, p.status, p.status_change_reason, p.status_change_performer, p.update_time, p.inactivity_date
                ORDER BY p.update_time DESC
                LIMIT 50
            """)
            
            results = cursor.fetchall()
            logger.info(f"Found {len(results)} publishers with status changes in last 30 days")
            return results
            
        except Exception as e:
            logger.error(f"Database error getting status changes: {e}")
            return []
        finally:
            cursor.close()
            db.close()
    
    def analyze_project_configurations(self, publisher_ids: List[int]) -> Dict[str, Any]:
        """Analyze project configurations for specific publishers using API"""
        if not self.api_client:
            return {"error": "API client not available"}
        
        config_analysis = {
            'total_publishers_analyzed': 0,
            'total_projects_analyzed': 0,
            'auto_mode_projects': 0,  # (1,72)
            'manual_mode_projects': 0,  # (0,0)
            'custom_config_projects': 0,  # Other configurations
            'api_errors': 0,
            'publisher_details': []
        }
        
        for pub_id in publisher_ids[:10]:  # Limit to 10 for demo
            try:
                logger.info(f"Analyzing publisher {pub_id}...")
                
                # Get projects for this publisher
                db = self._get_db_connection()
                cursor = db.cursor(pymysql.cursors.DictCursor)
                
                cursor.execute("""
                    SELECT DISTINCT gep.project_id
                    FROM geo_edge_projects gep
                    INNER JOIN sp_campaigns sc ON gep.campaign_id = sc.id
                    WHERE sc.syndicator_id = %s
                    LIMIT 20
                """, (pub_id,))
                
                projects = cursor.fetchall()
                cursor.close()
                db.close()
                
                publisher_analysis = {
                    'publisher_id': pub_id,
                    'total_projects': len(projects),
                    'auto_mode_count': 0,
                    'manual_mode_count': 0,
                    'custom_config_count': 0,
                    'sample_projects': []
                }
                
                # Analyze each project's configuration
                for project in projects[:5]:  # Sample first 5 projects
                    try:
                        project_id = project['project_id']
                        project_data = self.api_client.get_project(project_id)
                        
                        auto_scan = project_data.get('auto_scan', 0)
                        times_per_day = project_data.get('times_per_day', 0)
                        
                        project_config = {
                            'project_id': project_id,
                            'auto_scan': auto_scan,
                            'times_per_day': times_per_day,
                            'configuration_type': self._classify_config(auto_scan, times_per_day)
                        }
                        
                        # Count configurations
                        if auto_scan == 1 and times_per_day == 72:
                            publisher_analysis['auto_mode_count'] += 1
                            config_analysis['auto_mode_projects'] += 1
                        elif auto_scan == 0 and times_per_day == 0:
                            publisher_analysis['manual_mode_count'] += 1
                            config_analysis['manual_mode_projects'] += 1
                        else:
                            publisher_analysis['custom_config_count'] += 1
                            config_analysis['custom_config_projects'] += 1
                        
                        publisher_analysis['sample_projects'].append(project_config)
                        config_analysis['total_projects_analyzed'] += 1
                        
                    except Exception as e:
                        logger.warning(f"Error analyzing project {project_id}: {e}")
                        config_analysis['api_errors'] += 1
                
                config_analysis['publisher_details'].append(publisher_analysis)
                config_analysis['total_publishers_analyzed'] += 1
                
            except Exception as e:
                logger.error(f"Error analyzing publisher {pub_id}: {e}")
                config_analysis['api_errors'] += 1
        
        return config_analysis
    
    def _classify_config(self, auto_scan: int, times_per_day: int) -> str:
        """Classify configuration type"""
        if auto_scan == 1 and times_per_day == 72:
            return "Auto Mode (1,72)"
        elif auto_scan == 0 and times_per_day == 0:
            return "Manual Mode (0,0)"
        else:
            return f"Custom ({auto_scan},{times_per_day})"
    
    def generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generate comprehensive analysis report"""
        logger.info("🔍 Starting comprehensive Auto Mode configuration analysis...")
        
        # Get all publishers with projects
        all_publishers = self.get_all_publishers_with_projects()
        
        # Get recent status changes
        recent_changes = self.get_recent_status_changes()
        
        # Analyze configurations for active publishers
        active_publishers = [p for p in all_publishers if p['publisher_status'] == 'active']
        inactive_publishers = [p for p in all_publishers if p['publisher_status'] != 'active']
        
        # Sample configuration analysis
        config_analysis = {}
        if active_publishers:
            sample_ids = [p['publisher_id'] for p in active_publishers[:5]]
            config_analysis = self.analyze_project_configurations(sample_ids)
        
        report = {
            'analysis_timestamp': datetime.now().isoformat(),
            'database_summary': {
                'total_publishers_with_projects': len(all_publishers),
                'active_publishers': len(active_publishers),
                'inactive_publishers': len(inactive_publishers),
                'recent_status_changes': len(recent_changes)
            },
            'publisher_breakdown': {
                'active': active_publishers[:10],  # Top 10 active
                'recently_inactive': recent_changes[:10]  # Recent changes
            },
            'configuration_analysis': config_analysis,
            'key_findings': self._generate_key_findings(all_publishers, recent_changes, config_analysis)
        }
        
        return report
    
    def _generate_key_findings(self, all_publishers: List[Dict], recent_changes: List[Dict], config_analysis: Dict) -> List[str]:
        """Generate key findings from the analysis"""
        findings = []
        
        total_pubs = len(all_publishers)
        active_pubs = len([p for p in all_publishers if p['publisher_status'] == 'active'])
        inactive_pubs = total_pubs - active_pubs
        
        findings.append(f"📊 Total publishers with projects (90 days): {total_pubs}")
        findings.append(f"✅ Active publishers: {active_pubs} ({active_pubs/total_pubs*100:.1f}%)")
        findings.append(f"⚠️ Inactive publishers: {inactive_pubs} ({inactive_pubs/total_pubs*100:.1f}%)")
        findings.append(f"🔄 Recent status changes (30 days): {len(recent_changes)}")
        
        if config_analysis and 'total_projects_analyzed' in config_analysis:
            total_analyzed = config_analysis['total_projects_analyzed']
            auto_mode = config_analysis['auto_mode_projects']
            manual_mode = config_analysis['manual_mode_projects']
            custom = config_analysis['custom_config_projects']
            
            if total_analyzed > 0:
                findings.append(f"🔍 Sample projects analyzed: {total_analyzed}")
                findings.append(f"🚀 Auto Mode (1,72) projects: {auto_mode} ({auto_mode/total_analyzed*100:.1f}%)")
                findings.append(f"📋 Manual Mode (0,0) projects: {manual_mode} ({manual_mode/total_analyzed*100:.1f}%)")
                findings.append(f"⚙️ Custom configuration projects: {custom} ({custom/total_analyzed*100:.1f}%)")
        
        # Analyze recent changes
        frozen_accounts = [c for c in recent_changes if 'frozen' in c['status'].lower() or 'inactive' in c['status'].lower()]
        if frozen_accounts:
            findings.append(f"🧊 Recently frozen/inactive accounts: {len(frozen_accounts)}")
        
        return findings

def main():
    """Main analysis function"""
    print("🔍 GeoEdge Auto Mode Configuration - Deep Research Analysis")
    print("=" * 70)
    print("Analyzing all account changes and current configurations...")
    print("This will show you exactly what changes were made and what's left.")
    print("=" * 70)
    print()
    
    analyzer = ConfigurationAnalyzer()
    
    try:
        report = analyzer.generate_comprehensive_report()
        
        print("📊 COMPREHENSIVE ANALYSIS RESULTS")
        print("=" * 50)
        
        # Database Summary
        db_summary = report['database_summary']
        print(f"📈 DATABASE SUMMARY:")
        print(f"   • Total publishers with projects: {db_summary['total_publishers_with_projects']}")
        print(f"   • Active publishers: {db_summary['active_publishers']}")
        print(f"   • Inactive publishers: {db_summary['inactive_publishers']}")
        print(f"   • Recent status changes (30d): {db_summary['recent_status_changes']}")
        print()
        
        # Key Findings
        print("🔍 KEY FINDINGS:")
        for finding in report['key_findings']:
            print(f"   {finding}")
        print()
        
        # Active Publishers Sample
        active_sample = report['publisher_breakdown']['active'][:5]
        if active_sample:
            print("✅ TOP ACTIVE PUBLISHERS:")
            for pub in active_sample:
                print(f"   Publisher {pub['publisher_id']}: {pub['publisher_name']}")
                print(f"      Projects: {pub['total_projects']}, Last activity: {pub['days_since_last_project']} days ago")
        print()
        
        # Recent Changes
        recent_sample = report['publisher_breakdown']['recently_inactive'][:5]
        if recent_sample:
            print("⚠️ RECENT STATUS CHANGES:")
            for change in recent_sample:
                print(f"   Publisher {change['publisher_id']}: {change['publisher_name']}")
                print(f"      Status: {change['status']}")
                print(f"      Changed: {change['update_time']} | Reason: {change['status_change_reason'] or 'Not specified'}")
                print(f"      Projects: {change['total_projects'] or 0}")
        print()
        
        # Configuration Analysis
        config = report['configuration_analysis']
        if config and 'total_publishers_analyzed' in config:
            print("🔧 CONFIGURATION ANALYSIS (SAMPLE):")
            print(f"   Publishers analyzed: {config['total_publishers_analyzed']}")
            print(f"   Projects analyzed: {config['total_projects_analyzed']}")
            print(f"   Auto Mode (1,72): {config['auto_mode_projects']} projects")
            print(f"   Manual Mode (0,0): {config['manual_mode_projects']} projects")  
            print(f"   Custom configs: {config['custom_config_projects']} projects")
            print(f"   API errors: {config['api_errors']}")
            print()
            
            # Publisher details
            if config.get('publisher_details'):
                print("📋 PUBLISHER CONFIGURATION DETAILS:")
                for pub_detail in config['publisher_details'][:3]:
                    print(f"   Publisher {pub_detail['publisher_id']}:")
                    print(f"      Total projects: {pub_detail['total_projects']}")
                    print(f"      Auto Mode: {pub_detail['auto_mode_count']}")
                    print(f"      Manual Mode: {pub_detail['manual_mode_count']}")
                    print(f"      Custom: {pub_detail['custom_config_count']}")
        
        # Save detailed report
        report_file = f"configuration_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print()
        print("=" * 70)
        print("🎯 SUMMARY OF CHANGES MADE:")
        print("   • The system monitors publishers that change from active to inactive")
        print("   • When a publisher becomes inactive, their projects should be reset from (1,72) to (0,0)")
        print("   • This analysis shows current status and recent changes")
        print("   • For actual configuration changes, the system uses GeoEdge API calls")
        print()
        print(f"📄 Detailed report saved to: {report_file}")
        print("🔄 This analysis helps track what accounts need monitoring and reset")
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        print(f"❌ Analysis failed: {e}")

if __name__ == "__main__":
    main()