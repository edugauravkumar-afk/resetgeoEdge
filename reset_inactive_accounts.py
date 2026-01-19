#!/usr/bin/env python3
"""Reset auto_scan/times_per_day to 0/0 for frozen accounts."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Sequence, Tuple, cast

import pymysql
from pymysql import MySQLError
from dotenv import load_dotenv

from geoedge_projects.client import GeoEdgeClient
import update_autoscan

# Import email reporting
try:
    from email_reporter import GeoEdgeEmailReporter
    EMAIL_AVAILABLE = True
except ImportError:
    print("⚠️ Email reporting not available (email_reporter.py not found)")
    EMAIL_AVAILABLE = False

load_dotenv()

TARGET_ACCOUNTS: Sequence[str] = (
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
)

FROZEN_MARKERS = {
    "Frozen - Account is inactive",
    "Frozen - Account is manually paused",
    "Frozen - Account depleted (credit used up)",
}

SUCCESS_MARKERS = {"success", "ok", "updated"}


def _env_or_fail(key: str) -> str:
    value = os.getenv(key, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return value


def fetch_account_statuses(account_ids: Iterable[str]) -> Dict[str, str]:
    unique_ids = sorted({int(acc) for acc in account_ids if str(acc).isdigit()})
    if not unique_ids:
        return {}

    host = _env_or_fail("MYSQL_HOST")
    port = int(os.getenv("MYSQL_PORT", "3306"))
    user = _env_or_fail("MYSQL_USER")
    password = _env_or_fail("MYSQL_PASSWORD")
    database = _env_or_fail("MYSQL_DB")

    placeholders = ", ".join(["%s"] * len(unique_ids))
    sql = f"""
        WITH accounts_temp AS (
            SELECT 'Network' AS account_type,
                   n.network_id AS account_id,
                   n.is_depleted,
                   n.is_paused,
                   c.status AS publisher_status
            FROM trc.sp_network_syndication n
            JOIN trc.publishers c ON c.id = n.network_id
            WHERE n.network_id IN ({placeholders})
            UNION ALL
            SELECT 'Syndicator' AS account_type,
                   sb.syndicator_id AS account_id,
                   sb.is_depleted,
                   sv.is_paused,
                   c.status AS publisher_status
            FROM trc.sp_syndication_base sb
            LEFT JOIN trc.sp_syndication_v2 sv ON sb.syndicator_id = sv.syndicator_id
            JOIN trc.publishers c ON c.id = sb.syndicator_id
            WHERE sb.syndicator_id IN ({placeholders})
              AND sv.campaign_type = 'SPONSORED'
              AND sb.campaign_type = 'SPONSORED'
        )
        SELECT account_id,
               CASE
                   WHEN publisher_status != 'LIVE' THEN 'Frozen - Account is inactive'
                   WHEN is_paused = 1 THEN 'Frozen - Account is manually paused'
                   WHEN is_depleted = 1 THEN 'Frozen - Account depleted (credit used up)'
                   ELSE 'Active'
               END AS freeze_status
        FROM accounts_temp
        WHERE account_id IN ({placeholders})
    """

    params: Tuple[Any, ...] = tuple(unique_ids) * 3
    try:
        connection = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            cursorclass=pymysql.cursors.Cursor,
        )
    except MySQLError as exc:
        print(f"MySQL connection failed while fetching statuses: {exc}")
        return {}

    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return {str(account_id): status for account_id, status in cursor.fetchall()}
    finally:
        connection.close()


def fetch_projects_for_accounts(account_ids: Sequence[str], days: int = None, all_projects: bool = False) -> List[Dict[str, Any]]:
    if not account_ids:
        return []

    host = _env_or_fail("MYSQL_HOST")
    port = int(os.getenv("MYSQL_PORT", "3306"))
    user = _env_or_fail("MYSQL_USER")
    password = _env_or_fail("MYSQL_PASSWORD")
    database = _env_or_fail("MYSQL_DB")

    placeholders = ", ".join(["%s"] * len(account_ids))
    
    if all_projects:
        # For inactive accounts, get ALL projects regardless of creation date
        sql = f"""
            SELECT p.project_id,
                   p.campaign_id,
                   p.locations,
                   p.creation_date,
                   c.syndicator_id,
                   c.status as campaign_status
            FROM trc.geo_edge_projects p
            JOIN trc.sp_campaigns c ON p.campaign_id = c.id
            WHERE c.syndicator_id IN ({placeholders})
            ORDER BY p.creation_date DESC
        """
        params = tuple(account_ids)
    else:
        # For active accounts or specific lookback, use date filter
        sql = f"""
            SELECT p.project_id,
                   p.campaign_id,
                   p.locations,
                   p.creation_date,
                   c.syndicator_id,
                   c.status as campaign_status
            FROM trc.geo_edge_projects p
            JOIN trc.sp_campaigns c ON p.campaign_id = c.id
            WHERE c.syndicator_id IN ({placeholders})
              AND p.creation_date >= DATE_SUB(NOW(), INTERVAL %s DAY)
            ORDER BY p.creation_date DESC
        """
        params = tuple(account_ids) + (days or 30,)

    try:
        connection = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            cursorclass=pymysql.cursors.DictCursor,
        )
    except MySQLError as exc:
        print(f"MySQL connection failed while fetching projects: {exc}")
        return []

    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return list(cursor.fetchall())
    finally:
        connection.close()


def normalize_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def reset_projects(projects: List[Dict[str, Any]], *, dry_run: bool) -> List[Dict[str, Any]]:
    if not projects:
        return []

    session = update_autoscan.geoedge_session()
    client = GeoEdgeClient()
    results: List[Dict[str, Any]] = []

    for entry in projects:
        project_id = entry["project_id"]
        campaign_id = entry.get("campaign_id")
        account_id = entry.get("syndicator_id")

        try:
            project_data = cast(Dict[str, Any], client.get_project(project_id))  # type: ignore[no-any-return]
        except Exception as exc:
            results.append({
                "project_id": project_id,
                "campaign_id": campaign_id,
                "account_id": account_id,
                "status": "fetch-error",
                "detail": str(exc),
            })
            continue

        auto_scan = normalize_int(project_data.get("auto_scan"))
        times_per_day = normalize_int(project_data.get("times_per_day"))
        
        current_config = f"auto_scan={auto_scan}, times_per_day={times_per_day}"

        if auto_scan == 0 and times_per_day == 0:
            results.append({
                "project_id": project_id,
                "campaign_id": campaign_id,
                "account_id": account_id,
                "status": "already-zero",
                "detail": current_config,
            })
            continue
        
        # Log projects that need resetting (especially 1,72 -> 0,0)
        print(f"  Found project {project_id} (acct {account_id}) with config: {current_config} - NEEDS RESET")

        if dry_run:
            results.append({
                "project_id": project_id,
                "campaign_id": campaign_id,
                "account_id": account_id,
                "status": "dry-run",
                "detail": f"Would change from {current_config} to auto_scan=0, times_per_day=0",
            })
            continue

        try:
            response = cast(
                Dict[str, Any],
                update_autoscan.update_project_schedule(session, project_id, auto=0, times=0, dry_run=False),  # type: ignore[no-any-return]
            )
        except Exception as exc:
            results.append({
                "project_id": project_id,
                "campaign_id": campaign_id,
                "account_id": account_id,
                "status": "update-error",
                "detail": str(exc),
            })
            continue

        status_payload = cast(Dict[str, Any], response.get("status", {}))
        code = str(status_payload.get("code", "")).strip().lower()
        message = str(status_payload.get("message", "")).strip()

        if code not in SUCCESS_MARKERS and not any(marker in message.lower() for marker in SUCCESS_MARKERS):
            results.append({
                "project_id": project_id,
                "campaign_id": campaign_id,
                "account_id": account_id,
                "status": "api-rejected",
                "detail": message or code or "Unknown API response",
            })
            continue

        try:
            refreshed = cast(Dict[str, Any], client.get_project(project_id))  # type: ignore[no-any-return]
        except Exception as exc:
            results.append({
                "project_id": project_id,
                "campaign_id": campaign_id,
                "account_id": account_id,
                "status": "verify-error",
                "detail": str(exc),
            })
            continue

        final_auto = normalize_int(refreshed.get("auto_scan"))
        final_times = normalize_int(refreshed.get("times_per_day"))
        outcome = "reset" if final_auto == 0 and final_times == 0 else "partial"
        detail = f"auto_scan={final_auto}, times_per_day={final_times}"

        results.append({
            "project_id": project_id,
            "campaign_id": campaign_id,
            "account_id": account_id,
            "status": outcome,
            "detail": detail,
        })

    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reset GeoEdge projects to 0/0 for frozen accounts.")
    parser.add_argument(
        "--accounts-file",
        help="Optional path to file with account IDs (one per line). Defaults to baked-in list.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Lookback window (days) when selecting projects for ACTIVE accounts. Inactive accounts always get ALL projects.",
    )
    parser.add_argument(
        "--all-projects",
        action="store_true",
        help="Fetch ALL projects for all accounts, not just recent ones for active accounts",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only report which projects would be reset without calling the API",
    )
    return parser.parse_args()


def load_accounts(path: str | None) -> List[str]:
    if not path:
        return list(TARGET_ACCOUNTS)

    accounts: List[str] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            token = line.strip()
            if token:
                accounts.append(token)
    return accounts


def main() -> int:
    start_time = time.time()
    args = parse_args()
    account_ids = load_accounts(args.accounts_file)

    statuses = fetch_account_statuses(account_ids)
    frozen_accounts = [acc for acc, label in statuses.items() if label in FROZEN_MARKERS]
    live_accounts = [acc for acc, label in statuses.items() if label not in FROZEN_MARKERS]
    
    print(f"Detected {len(frozen_accounts)} frozen accounts and {len(live_accounts)} live accounts")
    
    # Get projects - ALL projects for frozen accounts, recent for live accounts (unless --all-projects specified)
    print(f"Fetching projects for inactive accounts (all projects) and active accounts ({'all projects' if args.all_projects else f'last {args.days} days'})")
    
    frozen_projects = []
    if frozen_accounts:
        frozen_projects = fetch_projects_for_accounts(frozen_accounts, all_projects=True)
        print(f"Found {len(frozen_projects)} total projects for {len(frozen_accounts)} inactive accounts")
    
    live_projects = []
    if live_accounts:
        if args.all_projects:
            live_projects = fetch_projects_for_accounts(live_accounts, all_projects=True)
            print(f"Found {len(live_projects)} total projects for {len(live_accounts)} live accounts")
        else:
            live_projects = fetch_projects_for_accounts(live_accounts, days=args.days, all_projects=False)
            print(f"Found {len(live_projects)} recent projects for {len(live_accounts)} live accounts")
    
    all_projects_data = frozen_projects + live_projects
    if not all_projects_data:
        print("No projects found for target accounts")
        return 0

    projects = {row["project_id"]: row for row in all_projects_data}
    print(f"Total projects to check: {len(projects)}")
    
    # Show account status breakdown
    print("\nAccount status breakdown:")
    for acc in frozen_accounts:
        status = statuses.get(acc, "Unknown")
        account_projects = [p for p in frozen_projects if str(p['syndicator_id']) == acc]
        print(f"  - INACTIVE Account {acc}: {status} ({len(account_projects)} total projects)")
    
    for acc in live_accounts:
        account_projects = [p for p in live_projects if str(p['syndicator_id']) == acc]
        if account_projects:  # Only show live accounts that have projects
            print(f"  - ACTIVE Account {acc}: Live ({len(account_projects)} recent projects)")
    
    # Focus reset efforts on inactive accounts primarily
    print(f"\n🎯 Priority: Resetting ALL projects for {len(frozen_accounts)} inactive accounts")
    print(f"📊 Also checking: Recent projects for {len([a for a in live_accounts if any(p['syndicator_id'] == int(a) for p in live_projects)])} active accounts")

    # Scan projects for configuration that needs resetting
    print("\nScanning projects for configuration that needs resetting...")
    client = GeoEdgeClient()
    projects_to_reset = []
    
    for project_data in all_projects_data:
        project_id = project_data["project_id"]
        account_id = str(project_data["syndicator_id"])
        account_status = statuses.get(account_id, "Unknown")
        is_inactive = account_status in FROZEN_MARKERS
        
        try:
            project_info = client.get_project(project_id)
            auto_scan = normalize_int(project_info.get("auto_scan"))
            times_per_day = normalize_int(project_info.get("times_per_day"))
            
            # Only include projects that need resetting (not already 0,0)
            if auto_scan != 0 or times_per_day != 0:
                project_data["current_auto_scan"] = auto_scan
                project_data["current_times_per_day"] = times_per_day
                project_data["is_inactive_account"] = is_inactive
                projects_to_reset.append(project_data)
                
                account_type = "INACTIVE" if is_inactive else "ACTIVE"
                priority = "🚨 HIGH PRIORITY" if is_inactive else "📋 Standard"
                print(f"  {priority}: {project_id} ({account_type} acct {account_id}) config {auto_scan},{times_per_day} -> NEEDS RESET")
                
        except Exception as e:
            print(f"  ❌ Error checking {project_id} (acct {account_id}): {e}")
    
    if not projects_to_reset:
        print("\n✅ All projects are already properly configured (0,0)!")
        return 0
    
    action = "Would reset" if args.dry_run else "Resetting"
    print(f"\n{action} {len(projects_to_reset)} projects from auto mode to manual mode (0,0)")
    
    results = reset_projects(projects_to_reset, dry_run=args.dry_run)

    reset_count = sum(1 for row in results if row["status"] == "reset")
    partial_count = sum(1 for row in results if row["status"] == "partial")
    already_zero = sum(1 for row in results if row["status"] == "already-zero")
    dry_runs = sum(1 for row in results if row["status"] == "dry-run")
    failures = [row for row in results if row["status"] not in {"reset", "partial", "already-zero"}]

    if results:
        print("\nPer-project details:")
        for row in results:
            project_id = row.get("project_id")
            account_id = row.get("account_id")
            campaign_id = row.get("campaign_id")
            status = row.get("status")
            detail = row.get("detail", "")
            print(f" - {project_id} | acct {account_id} | campaign {campaign_id} | {status} | {detail}")

    # Enhanced summary with breakdown by account type
    inactive_resets = sum(1 for row in results 
                         if row["status"] in {"reset", "dry-run"} 
                         and any(p.get("is_inactive_account", False) 
                               for p in projects_to_reset 
                               if p["project_id"] == row["project_id"]))
    
    changed_from_auto = sum(1 for row in results 
                          if row["status"] in {"reset", "dry-run"} 
                          and "auto_scan=1" in row.get("detail", ""))
    
    print("\n=== ENHANCED RESET SUMMARY ===")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print(f"Total projects processed: {len(results)}")
    print(f"Projects reset to 0/0: {reset_count}")
    print(f"  ├─ From INACTIVE accounts: {inactive_resets}")
    print(f"  └─ From ACTIVE accounts: {reset_count - inactive_resets}")
    print(f"Projects already at 0/0: {already_zero}")
    print(f"Projects with partial reset: {partial_count}")
    if dry_runs:
        print(f"Dry-run entries: {dry_runs}")
    if changed_from_auto > 0:
        print(f"🎯 Projects changed from AUTO mode (1,72) to MANUAL (0,0): {changed_from_auto}")
    print(f"Failures: {len(failures)}")

    if failures:
        print("\nFailures:")
        for row in failures:
            print(f" - {row['project_id']} (acct {row['account_id']}): {row['status']} -> {row['detail']}")

    # Send email report if enabled
    if EMAIL_AVAILABLE and not args.dry_run:
        try:
            # Prepare email report data
            report_data = {
                "total_accounts_checked": len(statuses),
                "inactive_accounts": len(frozen_accounts),
                "active_accounts": len(live_accounts), 
                "total_projects_scanned": len(results),
                "projects_reset": reset_count,
                "execution_time": time.time() - start_time if 'start_time' in locals() else 0,
                "status": "success" if not failures else "error",
                "error_message": f"{len(failures)} project updates failed" if failures else None,
                "inactive_account_details": [],
                "active_account_details": []
            }
            
            # Build account details for email
            for acc in frozen_accounts:
                account_projects = [p for p in frozen_projects if str(p['syndicator_id']) == acc]
                account_resets = sum(1 for r in results 
                                   if r.get('account_id') == acc and r.get('status') in {'reset', 'dry-run'})
                report_data["inactive_account_details"].append({
                    "account_id": acc,
                    "status": "INACTIVE", 
                    "project_count": len(account_projects),
                    "changes_made": account_resets
                })
            
            for acc in live_accounts:
                account_projects = [p for p in live_projects if str(p['syndicator_id']) == acc]
                if account_projects:  # Only include accounts with projects
                    account_resets = sum(1 for r in results 
                                       if r.get('account_id') == acc and r.get('status') in {'reset', 'dry-run'})
                    report_data["active_account_details"].append({
                        "account_id": acc,
                        "status": "ACTIVE",
                        "project_count": len(account_projects), 
                        "changes_made": account_resets
                    })
            
            # Send email report
            email_reporter = GeoEdgeEmailReporter()
            email_sent = email_reporter.send_daily_reset_report(report_data)
            
            if email_sent:
                print("📧 Email report sent successfully")
            else:
                print("⚠️ Failed to send email report")
                
        except Exception as e:
            print(f"⚠️ Email reporting error: {str(e)}")
    elif args.dry_run:
        print("📧 Email report skipped (dry-run mode)")
    elif not EMAIL_AVAILABLE:
        print("📧 Email report skipped (not configured)")

    if args.dry_run:
        return 0

    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
