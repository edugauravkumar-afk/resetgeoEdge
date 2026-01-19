#!/usr/bin/env python3
"""Diagnostic script to find all projects with 1,72 configuration for inactive accounts."""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List
from dotenv import load_dotenv
from geoedge_projects.client import GeoEdgeClient
import reset_inactive_accounts

load_dotenv()

def find_projects_with_auto_config() -> None:
    """Find all projects that still have auto configuration (1, 72) for inactive accounts."""
    print("=== Diagnostic: Finding projects with 1,72 configuration ===\n")
    
    # Load all target accounts
    account_ids = reset_inactive_accounts.TARGET_ACCOUNTS
    
    # Get account statuses
    print("Fetching account statuses...")
    statuses = reset_inactive_accounts.fetch_account_statuses(account_ids)
    
    # Get projects for all accounts (not just frozen) with extended lookback
    print("Fetching projects for all accounts (180 day lookback)...")
    project_rows = reset_inactive_accounts.fetch_projects_for_accounts(account_ids, 180)
    
    if not project_rows:
        print("No projects found!")
        return
    
    print(f"Found {len(project_rows)} total projects to check\n")
    
    # Check each project's configuration
    client = GeoEdgeClient()
    auto_mode_projects = []
    zero_mode_projects = []
    errors = []
    
    for i, project_data in enumerate(project_rows, 1):
        project_id = project_data["project_id"]
        account_id = str(project_data["syndicator_id"])
        campaign_id = project_data.get("campaign_id")
        account_status = statuses.get(account_id, "Unknown")
        
        if i % 10 == 0:
            print(f"Checked {i}/{len(project_rows)} projects...")
        
        try:
            project_info = client.get_project(project_id)
            auto_scan = reset_inactive_accounts.normalize_int(project_info.get("auto_scan"))
            times_per_day = reset_inactive_accounts.normalize_int(project_info.get("times_per_day"))
            
            project_details = {
                "project_id": project_id,
                "account_id": account_id,
                "campaign_id": campaign_id,
                "account_status": account_status,
                "auto_scan": auto_scan,
                "times_per_day": times_per_day,
                "config": f"{auto_scan},{times_per_day}"
            }
            
            # Check if it's in auto mode (1, 72 or similar)
            if auto_scan == 1 and times_per_day == 72:
                auto_mode_projects.append(project_details)
            elif auto_scan == 0 and times_per_day == 0:
                zero_mode_projects.append(project_details)
            else:
                # Other configurations
                project_details["config"] = f"{auto_scan},{times_per_day} (other)"
                auto_mode_projects.append(project_details)
                
        except Exception as e:
            errors.append({
                "project_id": project_id,
                "account_id": account_id,
                "error": str(e)
            })
    
    print(f"\\nCompleted checking {len(project_rows)} projects")
    print(f"Projects with 0,0 configuration: {len(zero_mode_projects)}")
    print(f"Projects with auto/other configuration: {len(auto_mode_projects)}")
    print(f"Errors: {len(errors)}")
    
    # Show projects that need attention
    if auto_mode_projects:
        print("\\n=== PROJECTS THAT NEED RESETTING ===")
        
        # Group by account status
        frozen_auto_projects = [p for p in auto_mode_projects 
                              if p["account_status"] in reset_inactive_accounts.FROZEN_MARKERS]
        live_auto_projects = [p for p in auto_mode_projects 
                            if p["account_status"] not in reset_inactive_accounts.FROZEN_MARKERS]
        
        if frozen_auto_projects:
            print(f"\\nFROZEN accounts with auto/non-zero config ({len(frozen_auto_projects)} projects):") 
            for project in frozen_auto_projects:
                print(f"  - {project['project_id']} | acct {project['account_id']} | "
                      f"campaign {project['campaign_id']} | {project['config']} | "
                      f"status: {project['account_status']}")
        
        if live_auto_projects:
            print(f"\\nLIVE accounts with auto/non-zero config ({len(live_auto_projects)} projects):")
            for project in live_auto_projects[:20]:  # Show first 20
                print(f"  - {project['project_id']} | acct {project['account_id']} | "
                      f"campaign {project['campaign_id']} | {project['config']} | "
                      f"status: {project['account_status']}")
            if len(live_auto_projects) > 20:
                print(f"    ... and {len(live_auto_projects) - 20} more")
    else:
        print("\\n✅ All projects are properly configured!")
    
    if errors:
        print(f"\\n=== ERRORS ({len(errors)}) ===")
        for error in errors[:10]:  # Show first 10 errors
            print(f"  - {error['project_id']} (acct {error['account_id']}): {error['error']}")
        if len(errors) > 10:
            print(f"    ... and {len(errors) - 10} more errors")

if __name__ == "__main__":
    find_projects_with_auto_config()