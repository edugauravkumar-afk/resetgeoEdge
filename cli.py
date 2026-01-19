\
import os
import argparse
import sys
import json
from typing import List

from dotenv import load_dotenv
from tabulate import tabulate

from geoedge_projects.client import GeoEdgeClient

DEFAULT_COUNTRIES = ["IT", "FR", "DE", "ES"]

def main(argv: List[str] = None) -> int:
    load_dotenv()  # load .env if present

    parser = argparse.ArgumentParser(
        description="List GeoEdge projects targeting given countries (default: IT,FR,DE,ES)"
    )
    parser.add_argument(
        "--countries",
        type=str,
        default=",".join(DEFAULT_COUNTRIES),
        help="Comma-separated country codes to match (e.g., IT,FR,DE,ES)",
    )
    parser.add_argument("--json", action="store_true", help="Output JSON instead of a table")
    parser.add_argument("--limit", type=int, default=1000, help="Page size when listing projects")
    parser.add_argument("--max-workers", type=int, default=12, help="Concurrency for details fetch")
    parser.add_argument("--debug", action="store_true", help="Print debug info to stderr")
    args = parser.parse_args(argv)

    try:
        client = GeoEdgeClient()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    countries = [c.strip().upper() for c in args.countries.split(",") if c.strip()]
    if args.debug:
        print(f"Target countries: {countries}", file=sys.stderr)

    try:
        projects = client.fetch_projects_with_locations(page_limit=args.limit, max_workers=args.max_workers)
    except Exception as e:
        print(f"Failed to fetch projects: {e}", file=sys.stderr)
        return 3

    filtered = client.filter_projects_by_country_codes(projects, countries)

    # Prepare display rows
    rows = []
    for p in filtered:
        rows.append({
            "id": p.get("id"),
            "name": p.get("name"),
            "auto_scan": p.get("auto_scan"),
            "times_per_day": p.get("times_per_day"),
            "locations": ",".join(sorted((p.get("locations") or {}).keys())) if isinstance(p.get("locations"), dict) else "",
        })

    if args.json:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
    else:
        if not rows:
            print("No projects matched the requested countries.")
        else:
            print(tabulate(rows, headers="keys", tablefmt="github"))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
