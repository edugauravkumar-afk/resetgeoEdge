\
import argparse
import os
import sys
from typing import List, Optional
import requests
from dotenv import load_dotenv

BASE_ENV = "GEOEDGE_API_BASE"
KEY_ENV = "GEOEDGE_API_KEY"


def geoedge_session() -> requests.Session:
    load_dotenv()
    base = os.getenv(BASE_ENV, "").rstrip("/")
    key = os.getenv(KEY_ENV)
    if not base or not key:
        print("Missing GEOEDGE_API_BASE or GEOEDGE_API_KEY in environment/.env", file=sys.stderr)
        sys.exit(2)
    s = requests.Session()
    s.headers.update({"Authorization": key})
    s.base_url = base
    return s


def api_url(s: requests.Session, path: str) -> str:
    if path.startswith("http"):
        return path
    return f"{s.base_url}{path}"


def get_project(s: requests.Session, project_id: str) -> dict:
    r = s.get(api_url(s, f"/projects/{project_id}"), timeout=60)
    try:
        data = r.json()
    except ValueError:
        r.raise_for_status()
        return {}
    if not r.ok and isinstance(data, dict) and "status" in data:
        raise requests.HTTPError(str(data["status"]), response=r)
    r.raise_for_status()
    # API response structure: {"response": {"project": {...}}, "status": {...}}
    response = data.get("response", {})
    return response.get("project", {})


def update_project_schedule(s: requests.Session, project_id: str, *, auto: Optional[int], times: Optional[int], dry_run: bool=False) -> dict:
    payload = {}
    if auto is not None:
        payload["auto_scan"] = int(auto)
    if times is not None:
        payload["times_per_day"] = int(times)

    if dry_run:
        return {"status": {"code": "DryRun", "message": f"Would PUT {payload} to /projects/{project_id}"}}

    r = s.put(api_url(s, f"/projects/{project_id}"), data=payload, timeout=60)
    try:
        data = r.json()
    except ValueError:
        r.raise_for_status()
        return {}
    if not r.ok and isinstance(data, dict) and "status" in data:
        raise requests.HTTPError(str(data["status"]), response=r)
    r.raise_for_status()
    return data


def scan_status(s: requests.Session, scan_ids: List[str]) -> dict:
    joined = ",".join(scan_ids)
    r = s.get(api_url(s, f"/projects/{joined}/scan-status"), timeout=60)
    try:
        data = r.json()
    except ValueError:
        r.raise_for_status()
        return {}
    if not r.ok and isinstance(data, dict) and "status" in data:
        raise requests.HTTPError(str(data["status"]), response=r)
    r.raise_for_status()
    return data


def main(argv: List[str] = None) -> int:
    p = argparse.ArgumentParser(description="Check & update GeoEdge project auto-scan frequency.")
    p.add_argument("project_ids", nargs="*", help="Project IDs to check/update")
    p.add_argument("--file", help="Path to file with project IDs (one per line)")
    p.add_argument("--check", action="store_true", help="Only check current schedule (no update)")
    p.add_argument("--auto", type=int, choices=[0,1], help="Set auto_scan 0 or 1")
    p.add_argument("--times", type=int, help="Set times_per_day (e.g., 72)")
    p.add_argument("--dry-run", action="store_true", help="Print what would change, don't PUT")
    p.add_argument("--scan-status", nargs="+", help="Check status of one or more scan IDs")

    args = p.parse_args(argv)

    s = geoedge_session()

    if args.scan_status:
        data = scan_status(s, args.scan_status)
        print(data)
        return 0

    ids = list(args.project_ids)
    if args.file:
        with open(args.file, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    ids.append(line)

    if not ids:
        print("Provide at least one project id (arg or --file).", file=sys.stderr)
        return 2

    for pid in ids:
        try:
            proj = get_project(s, pid)
        except Exception as e:
            print(f"[{pid}] ERROR fetching project: {e}", file=sys.stderr)
            continue

        name = proj.get("name")
        auto_scan = proj.get("auto_scan")
        times_per_day = proj.get("times_per_day")
        print(f"[{pid}] '{name}' current -> auto_scan={auto_scan}, times_per_day={times_per_day}")

        if args.check and args.auto is None and args.times is None:
            continue

        try:
            result = update_project_schedule(s, pid, auto=args.auto, times=args.times, dry_run=args.dry_run)
            print(f"[{pid}] update result -> {result}")
        except Exception as e:
            print(f"[{pid}] ERROR updating project: {e}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
