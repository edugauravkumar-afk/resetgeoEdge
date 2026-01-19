#!/usr/bin/env python3
"""
Verify all recent GeoEdge projects (IT/FR/DE/ES) and report those that don't have
auto_scan=1 and times_per_day=72. Writes failing project IDs to failed_projects.txt
for follow-up updates.
"""
import os
import time
import requests
import pymysql
from dotenv import load_dotenv

load_dotenv()

MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DB = os.getenv("MYSQL_DB")

API_KEY = os.getenv("GEOEDGE_API_KEY")
API_BASE = os.getenv("GEOEDGE_API_BASE", "https://api.geoedge.com/rest/analytics/v3").rstrip("/")

if not all([MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB, API_KEY]):
    print("Missing one or more required environment variables: MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB, GEOEDGE_API_KEY")
    raise SystemExit(2)


def get_project_ids():
    conn = pymysql.connect(host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER,
                           password=MYSQL_PASSWORD, database=MYSQL_DB,
                           charset="utf8mb4", cursorclass=pymysql.cursors.Cursor,
                           autocommit=True, read_timeout=60, write_timeout=60)

    sql = """
        SELECT DISTINCT p.project_id
        FROM trc.geo_edge_projects AS p
        JOIN trc.sp_campaign_inventory_instructions sii ON p.campaign_id = sii.campaign_id
        WHERE sii.instruction_status = 'ACTIVE'
          AND p.creation_date >= DATE_SUB(NOW(), INTERVAL 7 DAY)
          AND CONCAT(',', REPLACE(COALESCE(p.locations, ''), ' ', ''), ',') REGEXP ',(IT|FR|DE|ES),'
        ORDER BY p.creation_date DESC
    """

    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
            return [row[0] for row in rows]
    finally:
        conn.close()


def fetch_project(session, project_id):
    url = f"{API_BASE}/projects/{project_id}"
    r = session.get(url, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data.get('response', {}).get('project', {})


def main():
    print("🔎 Verifying recent GeoEdge projects for auto_scan=1 and times_per_day=72")
    pids = get_project_ids()
    total = len(pids)
    print(f"Found {total} projects to verify")

    s = requests.Session()
    s.headers.update({"Authorization": API_KEY})

    failing = []

    for i, pid in enumerate(pids, 1):
        try:
            proj = fetch_project(s, pid)
        except Exception as e:
            print(f"[{i}/{total}] {pid} - ERROR fetching: {e}")
            failing.append(pid)
            continue

        auto = proj.get('auto_scan')
        times = proj.get('times_per_day')
        if auto != 1 or times != 72:
            print(f"[{i}/{total}] {pid} -> auto_scan={auto}, times_per_day={times}  <-- FAIL")
            failing.append(pid)
        else:
            print(f"[{i}/{total}] {pid} -> auto_scan={auto}, times_per_day={times}")

        # small sleep to avoid bursting API
        time.sleep(0.25)

    # write failing ids
    out_path = os.path.join(os.getcwd(), 'failed_projects.txt')
    with open(out_path, 'w', encoding='utf-8') as fh:
        for pid in failing:
            fh.write(pid + "\n")

    print("\n✅ Verification complete")
    print(f"Total checked: {total}")
    print(f"Failing: {len(failing)} (written to {out_path})")


if __name__ == '__main__':
    main()
