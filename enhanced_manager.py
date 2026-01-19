#!/usr/bin/env python3
"""
ENHANCED GEOEDGE PROJECT MANAGER
Complete dashboard for managing GeoEdge project configurations
Features:
- Configurable lookback period
- Visual status indicators (green for correct config)
- One-click bulk update
- Real-time progress tracking
- Summary statistics
"""

import streamlit as st
import pandas as pd
import pymysql
import requests
import os
import time
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv("GEOEDGE_API_KEY")
BASE_URL = "https://api.geoedge.com/rest/analytics/v3"

# Page configuration
st.set_page_config(
    page_title="GeoEdge Project Manager",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_projects_from_database(days_back=7, locations=None):
    """Get projects from database with configurable lookback period"""
    
    host = os.getenv("MYSQL_HOST")
    port = int(os.getenv("MYSQL_PORT", "3306"))
    user = os.getenv("MYSQL_USER")
    password = os.getenv("MYSQL_PASSWORD")
    db = os.getenv("MYSQL_DB")

    conn = pymysql.connect(
        host=host, port=port, user=user, password=password, database=db,
        charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor,
        autocommit=True, read_timeout=60, write_timeout=60,
    )

    try:
        with conn.cursor() as cursor:
            # Build location filter
            location_filter = ""
            if locations:
                location_regex = "|".join(locations)
                location_filter = f"AND CONCAT(',', REPLACE(COALESCE(p.locations, ''), ' ', ''), ',') REGEXP ',({location_regex}),' "
            
            sql = f"""
                SELECT DISTINCT
                    p.project_id,
                    p.campaign_id,
                    p.locations,
                    p.creation_date,
                    sii.instruction_status
                FROM trc.geo_edge_projects AS p
                JOIN trc.sp_campaign_inventory_instructions sii ON p.campaign_id = sii.campaign_id
                WHERE sii.instruction_status = 'ACTIVE' 
                  AND p.creation_date >= DATE_SUB(NOW(), INTERVAL {days_back} DAY)
                  {location_filter}
                ORDER BY p.creation_date DESC
            """
            cursor.execute(sql)
            results = cursor.fetchall()
            return results
    finally:
        conn.close()

def get_project_api_status(project_id):
    """Get project's current API settings"""
    try:
        url = f"{BASE_URL}/projects/{project_id}"
        headers = {"Authorization": API_KEY}
        
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            result = response.json()
            if 'response' in result and 'project' in result['response']:
                project = result['response']['project']
                
                # Fix for API response data type issues - ensure values are integers
                auto_scan_value = project.get('auto_scan')
                times_per_day_value = project.get('times_per_day')
                
                # Convert to integers if they exist, otherwise use 0
                try:
                    auto_scan_value = int(auto_scan_value) if auto_scan_value is not None else 0
                except (ValueError, TypeError):
                    auto_scan_value = 0
                    
                try:
                    times_per_day_value = int(times_per_day_value) if times_per_day_value is not None else 0
                except (ValueError, TypeError):
                    times_per_day_value = 0
                
                return {
                    'auto_scan': auto_scan_value,
                    'times_per_day': times_per_day_value,
                    'project_name': project.get('name', 'Unknown'),
                    'api_accessible': True
                }
            
            # Log the issue for debugging
            print(f"API Response missing project data: {result}")
            return {'auto_scan': 0, 'times_per_day': 0, 'project_name': 'Invalid Response Format', 'api_accessible': False}
        
        # Log HTTP errors
        print(f"API Error: Status {response.status_code} for project {project_id}")
        try:
            error_detail = response.json()
            print(f"Error details: {error_detail}")
        except:
            print("Could not parse error response")
            
        return {'auto_scan': 0, 'times_per_day': 0, 'project_name': f'HTTP Error: {response.status_code}', 'api_accessible': False}
    except Exception as e:
        print(f"Exception in API call for {project_id}: {str(e)}")
        return {'auto_scan': 0, 'times_per_day': 0, 'project_name': f'Error: {str(e)}', 'api_accessible': False}

def update_project_settings(project_id, auto_scan_value, times_per_day_value):
    """Update project settings via API"""
    try:
        url = f"{BASE_URL}/projects/{project_id}"
        headers = {"Authorization": API_KEY, "Content-Type": "application/json"}
        
        # Ensure we're sending integers
        try:
            auto_scan_int = int(auto_scan_value)
        except (ValueError, TypeError):
            auto_scan_int = 1  # Default to 1 if conversion fails
            
        try:
            times_per_day_int = int(times_per_day_value)
        except (ValueError, TypeError):
            times_per_day_int = 72  # Default to 72 if conversion fails
        
        # Create data as JSON payload
        data = {
            "auto_scan": auto_scan_int,
            "times_per_day": times_per_day_int
        }
        
        print(f"Updating project {project_id} with data: {data}")
        
        # Use json parameter instead of data for proper JSON formatting
        response = requests.put(url, headers=headers, json=data, timeout=15)
        if response.status_code == 200:
            result = response.json()
            success = result.get('status', {}).get('code') == 'Success'
            if success:
                print(f"Successfully updated project {project_id}")
            else:
                print(f"Failed to update project {project_id}: {result}")
            return success
        else:
            print(f"HTTP Error updating project {project_id}: Status {response.status_code}")
            try:
                error_detail = response.json()
                print(f"Error details: {error_detail}")
            except:
                print("Could not parse error response")
            return False
    except Exception as e:
        print(f"Exception updating project {project_id}: {str(e)}")
        return False

def main():
    st.title("🎯 GeoEdge Project Manager")
    st.markdown("---")
    
    # Sidebar Configuration
    st.sidebar.header("📊 Configuration")
    
    # Lookback period configuration
    days_back = st.sidebar.number_input(
        "📅 Days to Look Back",
        min_value=1,
        max_value=365,
        value=7,
        help="Number of days back to fetch projects from"
    )
    
    # Location filter
    available_locations = ['IT', 'FR', 'DE', 'ES']
    selected_locations = st.sidebar.multiselect(
        "🌍 Target Locations",
        available_locations,
        default=available_locations,
        help="Select which countries to include"
    )
    
    # Target configuration
    st.sidebar.header("🎯 Target Configuration")
    target_auto_scan = st.sidebar.number_input("Auto Scan Value", min_value=0, max_value=1, value=1)
    target_times_per_day = st.sidebar.number_input("Times Per Day Value", min_value=0, max_value=1000, value=72)
    
    # Main content
    st.header(f"📋 Projects from Last {days_back} Days")
    
    # Load projects
    with st.spinner("🔍 Fetching projects from database..."):
        projects = get_projects_from_database(days_back, selected_locations)
    
    if not projects:
        st.warning(f"No projects found for the last {days_back} days with selected criteria.")
        return
    
    st.success(f"✅ Found {len(projects)} projects")
    
    # Display initial projects table (database data only)
    st.header("📋 Projects Table (Database Data)")
    
    # Convert to DataFrame for initial display
    initial_df = pd.DataFrame(projects)
    display_columns = ['project_id', 'campaign_id', 'locations', 'creation_date', 'instruction_status']
    display_df = initial_df[display_columns].copy()
    display_df.columns = ['Project ID', 'Campaign ID', 'Locations', 'Created', 'Status']
    
    st.dataframe(display_df, width="stretch", height=400)
    
    # Option to check API status and update configuration
    st.header("🔍 API Management")
    st.info(f"**Available Actions**: Check current configuration or update all {len(projects)} projects")
    
    # Two main action buttons
    col1, col2 = st.columns(2)
    
    with col1:
        check_all_button = st.button("🔍 Check current config for all projects", type="secondary")
    
    with col2:
        update_all_button = st.button("🎯 Update configuration for all projects", type="primary")
    
    if check_all_button:
        # Set flag to proceed with checking all projects
        st.session_state.proceed_with_api_check = True
        st.session_state.selected_projects = projects
        st.session_state.action_type = 'check'
    
    elif update_all_button:
        # Set confirmation needed flag
        st.session_state.show_confirmation = True
        st.session_state.selected_projects = projects
        st.session_state.action_type = 'smart_update'
    
    # Show confirmation dialog if update was clicked
    if st.session_state.get('show_confirmation', False):
        st.warning(f"⚠️ **BULK UPDATE CONFIRMATION**")
        st.info(f"This will check all **{len(projects)}** projects and update only those with incorrect configuration:\n- Auto Scan: **{target_auto_scan}**\n- Times Per Day: **{target_times_per_day}**")
        
        col_confirm, col_cancel = st.columns(2)
        with col_confirm:
            if st.button("✅ CONFIRM: Update Only Projects That Need Changes", type="primary", key="confirm_update"):
                st.session_state.proceed_with_bulk_update = True
                st.session_state.show_confirmation = False
                st.rerun()
        with col_cancel:
            if st.button("❌ Cancel", key="cancel_update"):
                st.session_state.show_confirmation = False
                st.rerun()
        return
    
    # Check if we should proceed with API checking
    if st.session_state.get('proceed_with_api_check', False):
        # Get the projects to check from session state
        projects_to_check = st.session_state.get('selected_projects', [])
    elif st.session_state.get('proceed_with_bulk_update', False):
        # Get the projects to update from session state
        projects_to_check = st.session_state.get('selected_projects', [])
    else:
        st.info("👆 Select an option above to check current configuration or update all projects")
        return
    
    # Determine action type
    action_type = st.session_state.get('action_type', 'check')
    
    # Store original total count for metrics
    total_original_projects = len(projects_to_check)
    
    if action_type == 'check':
        # API Status checking
        st.header("🔍 Checking Current API Status...")
        st.info(f"🎯 **Checking {len(projects_to_check)} projects** - Please wait while we fetch current configurations from GeoEdge API")
    else:
        # Direct bulk update
        st.header("🚀 Updating All Projects...")
        st.info(f"🎯 **Updating {len(projects_to_check)} projects** - Applying target configuration: Auto Scan={target_auto_scan}, Times Per Day={target_times_per_day}")
    
    # Enhanced Progress tracking
    progress_container = st.container()
    with progress_container:
        progress_bar = st.progress(0)
        status_text = st.empty()
        details_text = st.empty()
    
    # Real-time results table
    st.header("📊 Real-time Results")
    results_placeholder = st.empty()
    
    projects_with_status = []
    correct_count = 0
    updated_count = 0
    
    # Function to update the real-time results table
    def update_results_table():
        if projects_with_status:
            # Convert to DataFrame for display
            df = pd.DataFrame(projects_with_status)
            display_df = df[['project_id', 'campaign_id', 'locations', 'current_auto_scan', 'current_times_per_day', 'is_correct']].copy()
            display_df.columns = ['Project ID', 'Campaign ID', 'Countries', 'Auto Scan', 'Times/Day', 'Status']
            
            # Add status indicators
            display_df['Status'] = display_df['Status'].map({True: '✅ Correct', False: '⚠️ Needs Update'})
            
            # Color-code the dataframe
            def highlight_status(row):
                if '✅' in str(row['Status']):
                    return ['background-color: #90EE90'] * len(row)  # Light green
                else:
                    return ['background-color: #FFFFE0'] * len(row)  # Light yellow
            
            styled_df = display_df.style.apply(highlight_status, axis=1)
            
            # Update the table
            with results_placeholder.container():
                st.dataframe(styled_df, width="stretch", height=min(400, len(display_df) * 35 + 50))
                st.caption(f"📊 Processed: {len(projects_with_status)}/{len(projects_to_check)} | ✅ Correct: {correct_count}")
    
    if action_type == 'update' or action_type == 'smart_update':
        projects_needing_update = []
        processed_count = 0
        
        # For smart_update, we first check which projects actually need updates
        if action_type == 'smart_update':
            st.info("🔍 First checking which projects need updates...")
            
            # Process all projects to determine which need updates
            for i, project in enumerate(projects_to_check):
                project_id = project['project_id']
                processed_count += 1
                
                # Update checking progress
                progress = (i + 1) / len(projects_to_check)
                progress_bar.progress(progress, text=f"Checking: {i+1}/{len(projects_to_check)} projects")
                
                # Show current project being checked
                status_text.markdown(f"**🔍 Currently checking:** `{project_id}`")
                details_text.markdown(f"📊 Campaign: `{project.get('campaign_id', 'N/A')}` | 🌍 Countries: `{project.get('locations', 'N/A')}`")
                
                # Check API status
                api_status = get_project_api_status(project_id)
                
                if api_status['api_accessible']:
                    # Determine if configuration is correct or needs update
                    needs_update = (api_status['auto_scan'] != target_auto_scan or 
                                   api_status['times_per_day'] != target_times_per_day)
                    
                    if needs_update:
                        projects_needing_update.append({
                            'project_id': project_id,
                            'campaign_id': project.get('campaign_id', 'N/A'),
                            'locations': project.get('locations', 'N/A'),
                            'current_auto_scan': api_status['auto_scan'],
                            'current_times_per_day': api_status['times_per_day']
                        })
                        
                        # Add to results display but mark as needing update
                        project_data = {
                            'project_id': project_id,
                            'campaign_id': project.get('campaign_id', 'N/A'),
                            'locations': project.get('locations', 'N/A'),
                            'creation_date': project.get('creation_date', 'N/A'),
                            'status': project.get('instruction_status', 'ACTIVE'),
                            'project_name': api_status['project_name'],
                            'current_auto_scan': api_status['auto_scan'],
                            'current_times_per_day': api_status['times_per_day'],
                            'api_accessible': api_status['api_accessible'],
                            'is_correct': False,
                            'needs_update': True
                        }
                        projects_with_status.append(project_data)
                    else:
                        # Project is already correctly configured - add to results
                        project_data = {
                            'project_id': project_id,
                            'campaign_id': project.get('campaign_id', 'N/A'),
                            'locations': project.get('locations', 'N/A'),
                            'creation_date': project.get('creation_date', 'N/A'),
                            'status': project.get('instruction_status', 'ACTIVE'),
                            'project_name': api_status['project_name'],
                            'current_auto_scan': api_status['auto_scan'],
                            'current_times_per_day': api_status['times_per_day'],
                            'api_accessible': api_status['api_accessible'],
                            'is_correct': True,
                            'needs_update': False
                        }
                        projects_with_status.append(project_data)
                else:
                    # API not accessible - add to results with error status
                    project_data = {
                        'project_id': project_id,
                        'campaign_id': project.get('campaign_id', 'N/A'),
                        'locations': project.get('locations', 'N/A'),
                        'creation_date': project.get('creation_date', 'N/A'),
                        'status': project.get('instruction_status', 'ACTIVE'),
                        'project_name': api_status['project_name'],
                        'current_auto_scan': api_status['auto_scan'],
                        'current_times_per_day': api_status['times_per_day'],
                        'api_accessible': False,
                        'is_correct': False,
                        'needs_update': False
                    }
                    projects_with_status.append(project_data)
                
                # Update the real-time table during checking
                if i % 5 == 0:  # Update table every 5 projects to avoid too many refreshes
                    update_results_table()
                
                time.sleep(0.1)
            
            # Show results of the check
            st.success(f"✅ Check complete! Found {len(projects_needing_update)} projects that need updates.")
            
            # Reset for update phase
            projects_to_check = projects_needing_update
            progress_bar.progress(0)
            
        # Update only projects that need it (all for regular update, or filtered list for smart update)
        total_to_update = len(projects_to_check)
        
        if total_to_update == 0:
            st.success("✅ All projects already have the correct configuration! No updates needed.")
            return
        
        st.info(f"🚀 Updating {total_to_update} projects...")
        
        # Reset projects_with_status if we're doing smart update since we want fresh data
        if action_type == 'smart_update':
            projects_with_status = []
            
        for i, project in enumerate(projects_to_check):
            project_id = project['project_id']
            
            # Update progress
            progress = (i + 1) / total_to_update
            progress_bar.progress(progress, text=f"Progress: {i+1}/{total_to_update} projects updated")
            
            # Show current project being updated
            status_text.markdown(f"**🚀 Currently updating:** `{project_id}`")
            details_text.markdown(f"📊 Campaign: `{project.get('campaign_id', 'N/A')}` | 🌍 Countries: `{project.get('locations', 'N/A')}`")
            
            # Perform update
            if update_project_settings(project_id, target_auto_scan, target_times_per_day):
                updated_count += 1
                # Create project data assuming successful update
                project_data = {
                    'project_id': project_id,
                    'campaign_id': project.get('campaign_id', 'N/A'),
                    'locations': project.get('locations', 'N/A'),
                    'creation_date': project.get('creation_date', 'N/A'),
                    'status': project.get('instruction_status', 'ACTIVE'),
                    'project_name': 'Updated',
                    'current_auto_scan': target_auto_scan,
                    'current_times_per_day': target_times_per_day,
                    'api_accessible': True,
                    'is_correct': True,
                    'needs_update': False
                }
                correct_count += 1
            else:
                # Failed update
                project_data = {
                    'project_id': project_id,
                    'campaign_id': project.get('campaign_id', 'N/A'),
                    'locations': project.get('locations', 'N/A'),
                    'creation_date': project.get('creation_date', 'N/A'),
                    'status': project.get('instruction_status', 'ACTIVE'),
                    'project_name': 'Update Failed',
                    'current_auto_scan': 0,
                    'current_times_per_day': 0,
                    'api_accessible': False,
                    'is_correct': False,
                    'needs_update': True
                }
            
            projects_with_status.append(project_data)
            
            # Update the real-time table
            update_results_table()
            
            time.sleep(0.5)  # Longer delay for updates
        
    else:
        # Check current configuration first
        for i, project in enumerate(projects_to_check):
            project_id = project['project_id']
            
            # Update progress with enhanced display
            progress = (i + 1) / len(projects_to_check)
            progress_bar.progress(progress, text=f"Progress: {i+1}/{len(projects_to_check)} projects checked")
            
            # Show current project being checked
            status_text.markdown(f"**🔍 Currently checking:** `{project_id}`")
            details_text.markdown(f"📊 Campaign: `{project.get('campaign_id', 'N/A')}` | 🌍 Countries: `{project.get('locations', 'N/A')}`")
            
            # Get API status
            api_status = get_project_api_status(project_id)
            
            # Determine if configuration is correct
            is_correct = (api_status['auto_scan'] == target_auto_scan and 
                         api_status['times_per_day'] == target_times_per_day)
            
            if is_correct:
                correct_count += 1
            
            # Combine data
            project_data = {
                'project_id': project_id,
                'campaign_id': project['campaign_id'],
                'locations': project['locations'],
                'creation_date': project['creation_date'],
                'status': project['instruction_status'],
                'project_name': api_status['project_name'],
                'current_auto_scan': api_status['auto_scan'],
                'current_times_per_day': api_status['times_per_day'],
                'api_accessible': api_status['api_accessible'],
                'is_correct': is_correct,
                'needs_update': not is_correct and api_status['api_accessible']
            }
            
            projects_with_status.append(project_data)
            
            # Update the real-time table
            update_results_table()
            
            time.sleep(0.1)  # Small delay to avoid rate limiting
    
    # Clear progress indicators and show completion
    if action_type == 'update':
        progress_bar.progress(1.0, text=f"✅ Completed! Updated {len(projects_to_check)} projects")
        status_text.markdown(f"**🎉 Bulk Update Complete!**")
        details_text.markdown(f"📊 **Results:** {updated_count} successfully updated, {len(projects_to_check) - updated_count} failed")
    elif action_type == 'smart_update':
        progress_bar.progress(1.0, text=f"✅ Completed! Updated {updated_count} projects")
        status_text.markdown(f"**🎉 Smart Update Complete!**")
        
        # Calculate how many projects were already correctly configured
        # Use total_original_projects since projects_to_check may have been filtered
        total_needing_update = len([p for p in projects_with_status if p.get('needs_update', False)])
        already_correct = total_original_projects - total_needing_update
        
        # Show both updated count and already correct count
        details_text.markdown(f"📊 **Results:** {updated_count} successfully updated, {already_correct} already correctly configured")
    else:
        progress_bar.progress(1.0, text=f"✅ Completed! Checked {len(projects_to_check)} projects")
        status_text.markdown(f"**🎉 API Status Check Complete!**")
        details_text.markdown(f"📊 **Results:** {correct_count} correctly configured, {len(projects_to_check) - correct_count} need attention")
    
    # Clear session state to reset for next operation
    if 'proceed_with_api_check' in st.session_state:
        del st.session_state.proceed_with_api_check
    if 'proceed_with_bulk_update' in st.session_state:
        del st.session_state.proceed_with_bulk_update
    if 'selected_projects' in st.session_state:
        del st.session_state.selected_projects
    if 'action_type' in st.session_state:
        del st.session_state.action_type
    if 'show_confirmation' in st.session_state:
        del st.session_state.show_confirmation
    
    # Summary Statistics
    st.header("📊 Configuration Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Use original total for display, not filtered list
    total_projects = total_original_projects
    
    # Check if this was a smart update or a check operation
    if action_type == 'smart_update':
        with col1:
            st.metric("📋 Total Projects", total_projects)
        
        with col2:
            # For smart update, we display updated count
            st.metric("✅ Successfully Updated", updated_count)
        
        with col3:
            # For smart update, we show how many projects didn't need updating
            total_needing_update = len([p for p in projects_with_status if p.get('needs_update', False)])
            already_correct = total_projects - total_needing_update
            st.metric("✓ Already Correct", already_correct)
        
        with col4:
            api_error_count = len([p for p in projects_with_status if not p.get('api_accessible', True)])
            st.metric("⚠️ API Errors", api_error_count)
    else:
        # Regular check operation metrics
        with col1:
            st.metric("📋 Total Checked", total_projects)
        
        with col2:
            percent_correct = (correct_count/total_projects*100) if total_projects > 0 else 0
            st.metric("✅ Correctly Configured", correct_count, delta=f"{percent_correct:.1f}%")
        
        with col3:
            needs_update_count = len([p for p in projects_with_status if p.get('needs_update', False)])
            st.metric("🔧 Needs Update", needs_update_count)
        
        with col4:
            api_error_count = len([p for p in projects_with_status if not p.get('api_accessible', True)])
            st.metric("⚠️ API Errors", api_error_count)
    
    # Configuration Update Section
    # Calculate needs_update_count for all action types
    needs_update_count = len([p for p in projects_with_status if p.get('needs_update', False)])
    
    if needs_update_count > 0:
        st.header("🔧 Update Configuration")
        
        st.info(f"**Target Configuration:** auto_scan={target_auto_scan}, times_per_day={target_times_per_day}")
        
        if st.button(f"🚀 Update {needs_update_count} Projects", type="primary"):
            update_progress = st.progress(0)
            update_status = st.empty()
            
            updated_count = 0
            failed_count = 0
            
            projects_to_update = [p for p in projects_with_status if p.get('needs_update', False)]
            
            for i, project in enumerate(projects_to_update):
                project_id = project['project_id']
                
                # Update progress
                progress = (i + 1) / len(projects_to_update)
                update_progress.progress(progress)
                update_status.text(f"Updating project {i+1}/{len(projects_to_update)}: {project_id[:12]}...")
                
                # Perform update
                if update_project_settings(project_id, target_auto_scan, target_times_per_day):
                    updated_count += 1
                    # Update the project status in our data
                    project['current_auto_scan'] = target_auto_scan
                    project['current_times_per_day'] = target_times_per_day
                    project['is_correct'] = True
                    project['needs_update'] = False
                else:
                    failed_count += 1
                
                time.sleep(0.5)  # Delay between updates
            
            # Clear progress indicators
            update_progress.empty()
            update_status.empty()
            
            # Show results
            if updated_count == len(projects_to_update):
                st.success(f"🎉 Successfully updated all {updated_count} projects!")
            else:
                st.warning(f"⚠️ Updated {updated_count}/{len(projects_to_update)} projects. {failed_count} failed.")
            
            # Refresh the page data
            st.rerun()
    
    # Projects Table
    st.header("📋 Projects Table")
    
    # Convert to DataFrame for display
    df = pd.DataFrame(projects_with_status)
    
    # Prepare display DataFrame
    display_df = df[['project_id', 'campaign_id', 'locations', 'creation_date', 'status', 
                    'current_auto_scan', 'current_times_per_day', 'is_correct']].copy()
    
    display_df.columns = ['Project ID', 'Campaign ID', 'Locations', 'Created', 'Status', 
                         'Auto Scan', 'Times/Day', 'Correct Config']
    
    # Color-code the dataframe
    def highlight_correct_config(row):
        if row['Correct Config']:
            return ['background-color: #90EE90'] * len(row)  # Light green
        elif not df.loc[row.name, 'api_accessible']:
            return ['background-color: #FFB6C1'] * len(row)  # Light red for API errors
        else:
            return ['background-color: #FFFFE0'] * len(row)  # Light yellow for needs update
    
    styled_df = display_df.style.apply(highlight_correct_config, axis=1)
    
    st.dataframe(styled_df, width="stretch", height=400)
    
    # Legend
    st.markdown("""
    **Color Legend:**
    - 🟢 **Green**: Correctly configured projects
    - 🟡 **Yellow**: Projects that need updates
    - 🔴 **Red**: Projects with API access issues
    """)
    
    # Download option
    if st.button("📥 Download Report as CSV"):
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"geoedge_projects_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

if __name__ == "__main__":
    main()