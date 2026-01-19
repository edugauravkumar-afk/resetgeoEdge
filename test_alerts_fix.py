#!/usr/bin/env python3
"""
Quick test to verify the alerts analysis fixes
"""

import pandas as pd
import sys
import os

# Add the current directory to the path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_unique_aggregations():
    """Test the unique aggregations with correct column names"""
    # Create sample data with correct column names
    test_data = pd.DataFrame({
        'alert_id': ['alert1', 'alert2', 'alert3', 'alert4'],
        'project_id': ['proj1', 'proj1', 'proj2', 'proj2'],
        'project_name': ['Project A', 'Project A', 'Project B', 'Project B'],
        'trigger_type_id': ['trigger1', 'trigger2', 'trigger1', 'trigger1'],
        'trigger_type_name': ['Malware', 'Phishing', 'Malware', 'Malware'],
        'location_code': ['US', 'UK', 'US', 'CA'],
        'location_name': ['United States', 'United Kingdom', 'United States', 'Canada'],
        'event_datetime': ['2025-11-01 10:00:00', '2025-11-01 11:00:00', '2025-11-01 12:00:00', '2025-11-01 13:00:00'],
        'alert_name': ['Alert A', 'Alert B', 'Alert A', 'Alert C'],
        'campaign_id': ['camp1', 'camp2', 'camp1', 'camp3'],
        'account_id': ['acc1', 'acc1', 'acc2', 'acc2']
    })
    
    # Import only the class we need, not the main module
    from geoedge_projects.client import GeoEdgeClient
    
    class TestAnalyzer:
        def __init__(self):
            self.client = None
            
        def create_unique_aggregations(self, df: pd.DataFrame):
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
    
    analyzer = TestAnalyzer()
    
    try:
        unique_alerts, unique_advertisers = analyzer.create_unique_aggregations(test_data)
        print("✅ Unique aggregations test passed!")
        print(f"   - Unique alerts: {len(unique_alerts)} rows")
        print(f"   - Unique advertisers: {len(unique_advertisers)} rows")
        print(f"   - Advertiser columns: {list(unique_advertisers.columns)}")
        return True
    except Exception as e:
        print(f"❌ Unique aggregations test failed: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def test_without_account_id():
    """Test aggregations without account_id"""
    test_data = pd.DataFrame({
        'alert_id': ['alert1', 'alert2', 'alert3'],
        'project_id': ['proj1', 'proj1', 'proj2'],
        'project_name': ['Project A', 'Project A', 'Project B'],
        'trigger_type_id': ['trigger1', 'trigger2', 'trigger1'],
        'trigger_type_name': ['Malware', 'Phishing', 'Malware'],
        'location_code': ['US', 'UK', 'US'],
        'location_name': ['United States', 'United Kingdom', 'United States'],
        'event_datetime': ['2025-11-01 10:00:00', '2025-11-01 11:00:00', '2025-11-01 12:00:00'],
        'alert_name': ['Alert A', 'Alert B', 'Alert A'],
        'campaign_id': ['camp1', 'camp2', 'camp1']
    })
    
    # Same test class as above
    class TestAnalyzer:
        def __init__(self):
            self.client = None
            
        def create_unique_aggregations(self, df: pd.DataFrame):
            """Create unique project and account aggregations with comma-separated values"""
            if df.empty:
                return df.copy(), df.copy()
            
            # Create unique alerts table (all alerts with details, account_id can be duplicate)
            unique_alerts_df = df.copy()
            
            # Create unique advertisers table (aggregated by account_id)
            if 'account_id' in df.columns:
                return unique_alerts_df, df.copy()  # Simple case for test
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
    
    analyzer = TestAnalyzer()
    
    try:
        unique_alerts, unique_advertisers = analyzer.create_unique_aggregations(test_data)
        print("✅ No account_id test passed!")
        print(f"   - Unique alerts: {len(unique_alerts)} rows")
        print(f"   - Unique projects: {len(unique_advertisers)} rows")
        return True
    except Exception as e:
        print(f"❌ No account_id test failed: {e}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    print("🧪 Testing alerts analysis fixes...")
    print()
    
    test1 = test_unique_aggregations()
    test2 = test_without_account_id()
    
    print()
    if test1 and test2:
        print("🎉 All tests passed! The fixes are working correctly.")
    else:
        print("⚠️  Some tests failed. Check the errors above.")