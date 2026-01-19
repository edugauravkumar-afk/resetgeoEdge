\
import argparse
import os
import sys
from typing import List, Tuple

from dotenv import load_dotenv
from tabulate import tabulate
import pandas as pd

# Optional imports are local to chosen DB
import pymysql
import vertica_python

# Import GeoEdge client for fetching project details
from geoedge_projects.client import GeoEdgeClient


def build_regex(countries_csv: str) -> str:
    countries = [c.strip().upper() for c in countries_csv.split(",") if c.strip()]
    if not countries:
        raise ValueError("At least one country code is required")
    # Comma-safe pattern, e.g. ",(IT|FR|DE|ES),"
    pattern = ",(" + "|".join(sorted(set(countries))) + "),"
    return pattern


def query_mysql(days: int, regex: str, limit: int) -> List[Tuple]:
    host = os.getenv("MYSQL_HOST")
    port = int(os.getenv("MYSQL_PORT", "3306"))
    user = os.getenv("MYSQL_USER")
    password = os.getenv("MYSQL_PASSWORD")
    db = os.getenv("MYSQL_DB")
    auth_plugin = os.getenv("MYSQL_AUTH_PLUGIN") or "mysql_native_password"

    if not (host and user and password and db):
        raise RuntimeError("Missing MySQL env vars (MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB)")

    conn = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=db,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.Cursor,
        client_flag=0,
        autocommit=True,
        read_timeout=60,
        write_timeout=60,
    )
    try:
        with conn.cursor() as cur:
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
                  AND p.creation_date >= DATE_SUB(NOW(), INTERVAL %s DAY)
                  AND CONCAT(',', REPLACE(COALESCE(p.locations, ''), ' ', ''), ',') REGEXP %s
                ORDER BY p.creation_date DESC
                LIMIT {int(limit)}
            """
            cur.execute(sql, (days, regex))
            rows = cur.fetchall()
            return rows
    finally:
        conn.close()


def query_vertica(days: int, regex: str, limit: int) -> List[Tuple]:
    host = os.getenv("VERTICA_HOST")
    port = int(os.getenv("VERTICA_PORT", "5433"))
    user = os.getenv("VERTICA_USER")
    password = os.getenv("VERTICA_PASSWORD")
    db = os.getenv("VERTICA_DB")

    if not (host and user and password and db):
        raise RuntimeError("Missing Vertica env vars (VERTICA_HOST, VERTICA_USER, VERTICA_PASSWORD, VERTICA_DB)")

    conn_info = {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "database": db,
        "autocommit": True,
        "connection_timeout": 10,
        "unicode_error": "replace",
        "log_level": 0,
    }
    with vertica_python.connect(**conn_info) as connection:
        with connection.cursor() as cur:
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
                  AND p.creation_date >= NOW() - INTERVAL '{days} DAYS'
                  AND REGEXP_LIKE(',' || REPLACE(COALESCE(p.locations, ''), ' ', '') || ',', %s)
                ORDER BY p.creation_date DESC
                LIMIT {int(limit)}
            """
            cur.execute(sql, (regex,))
            rows = cur.fetchall()
            return rows


def fetch_project_details(project_ids: List[str]) -> dict:
    """Fetch auto_scan and times_per_day details from GeoEdge API for given project IDs"""
    try:
        client = GeoEdgeClient()
        project_details = {}
        
        for project_id in project_ids:
            try:
                project_data = client.get_project(project_id)
                # Debug: print the structure to understand the response
                # print(f"Debug: Project {project_id} data: {project_data}", file=sys.stderr)
                project_details[project_id] = {
                    'auto_scan': project_data.get('auto_scan', 'N/A'),
                    'times_per_day': project_data.get('times_per_day', 'N/A')
                }
            except Exception as e:
                print(f"Warning: Could not fetch details for project {project_id}: {e}", file=sys.stderr)
                project_details[project_id] = {
                    'auto_scan': 'Error',
                    'times_per_day': 'Error'
                }
        
        return project_details
    except Exception as e:
        print(f"Warning: Could not initialize GeoEdge client: {e}", file=sys.stderr)
        # Return empty dict so the rest of the script continues with N/A values
        return {pid: {'auto_scan': 'API_Error', 'times_per_day': 'API_Error'} for pid in project_ids}


def main(argv: List[str] = None) -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Query projects in last N days targeting given countries.")
    parser.add_argument("--db", choices=["mysql", "vertica"], default="mysql", help="Database to query")
    parser.add_argument("--days", type=int, default=7, help="Lookback window in days (rolling)")
    parser.add_argument("--countries", type=str, default="IT,FR,DE,ES", help="Comma-separated country codes")
    parser.add_argument("--limit", type=int, default=1000, help="Row limit (server-side)")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of table")
    parser.add_argument("--excel", type=str, help="Export to Excel file (provide filename, e.g., results.xlsx)")
    args = parser.parse_args(argv)

    regex = build_regex(args.countries)

    if args.db == "mysql":
        rows = query_mysql(args.days, regex, args.limit)
    else:
        rows = query_vertica(args.days, regex, args.limit)

    # Extract project IDs for fetching additional details
    project_ids = [row[0] for row in rows]  # project_id is the first column
    project_details = fetch_project_details(project_ids)

    headers = ["SNo", "project_id", "campaign_id", "locations", "creation_date", "instruction_status", "auto_scan", "times_per_day"]
    
    # Add serial numbers and project details to rows
    enhanced_rows = []
    for i, row in enumerate(rows, 1):
        project_id = row[0]
        details = project_details.get(project_id, {'auto_scan': 'N/A', 'times_per_day': 'N/A'})
        enhanced_row = (i,) + row + (details['auto_scan'], details['times_per_day'])
        enhanced_rows.append(enhanced_row)

    if args.excel:
        # Export to Excel
        df = pd.DataFrame(enhanced_rows, columns=headers)
        df.to_excel(args.excel, index=False, engine='openpyxl')
        print(f"Results exported to {args.excel}")
    elif args.json:
        import json
        as_dicts = [dict(zip(headers, r)) for r in enhanced_rows]
        print(json.dumps(as_dicts, indent=2, default=str, ensure_ascii=False))
    else:
        print(tabulate(enhanced_rows, headers=headers, tablefmt="github"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
