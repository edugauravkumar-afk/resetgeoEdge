#!/usr/bin/env python3
# pyright: ignore-all
"""Fetch all GeoEdge alerts for the last N days and export them to Excel."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, cast

import pandas as pd
from dotenv import load_dotenv

from geoedge_projects.client import GeoEdgeClient


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Download full GeoEdge alert history")
    parser.add_argument("--days", type=int, default=90, help="Lookback window in days")
    parser.add_argument(
        "--chunk-days",
        type=int,
        default=15,
        help="Chunk size in days for paged API requests (smaller avoids timeouts)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=200,
        help="Safety limit for pages per chunk (page size is fixed at 5000)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional path to Excel file. If omitted, timestamped file is created",
    )
    return parser


def chunk_range(start: datetime, end: datetime, delta_days: int) -> Iterable[Tuple[datetime, datetime]]:
    cursor = start
    delta = timedelta(days=delta_days)
    while cursor < end:
        next_cursor = min(cursor + delta, end)
        yield cursor, next_cursor
        cursor = next_cursor


def extract_project(alert: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    project_map_raw = alert.get("project_name")
    project_map: Dict[str, Any] = cast(Dict[str, Any], project_map_raw) if isinstance(project_map_raw, dict) else {}
    if project_map:
        project_id, project_name = next(iter(project_map.items()))
        return str(project_id), str(project_name)
    return None, None


def extract_location(alert: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    location_map_raw = alert.get("location")
    location_map: Dict[str, Any] = cast(Dict[str, Any], location_map_raw) if isinstance(location_map_raw, dict) else {}
    if location_map:
        location_code, location_name = next(iter(location_map.items()))
        return str(location_code), str(location_name)
    return None, None


def guess_campaign_id(project_name: Optional[str]) -> Optional[str]:
    if not project_name:
        return None
    parts = project_name.split("_")
    for part in parts:
        stripped = part.strip()
        if stripped.isdigit() and len(stripped) >= 7:
            return stripped
    return None


def flatten_alert(alert: Dict[str, Any]) -> Dict[str, Any]:
    project_id, project_name = extract_project(alert)
    location_code, location_name = extract_location(alert)
    security_urls_raw = alert.get("security_incident_urls")
    security_urls: List[str]
    if isinstance(security_urls_raw, list):
        security_urls = [str(url) for url in security_urls_raw]
    else:
        security_urls = []

    tag_raw = alert.get("tag")
    tag_block: Dict[str, Any] = cast(Dict[str, Any], tag_raw) if isinstance(tag_raw, dict) else {}

    flattened = {
        "alert_id": alert.get("alert_id"),
        "event_datetime": alert.get("event_datetime"),
        "alert_name": alert.get("alert_name"),
        "alert_details_url": alert.get("alert_details_url"),
        "trigger_type_id": alert.get("trigger_type_id"),
        "trigger_metadata": alert.get("trigger_metadata"),
        "project_id": project_id,
        "project_name": project_name,
        "campaign_id_guess": guess_campaign_id(project_name),
        "location_code": location_code,
        "location_name": location_name,
        "tag_id": alert.get("tag_id") or tag_block.get("id"),
        "tag_name": tag_block.get("name"),
        "tag_url": alert.get("tag_url") or tag_block.get("url"),
        "landing_page_url": alert.get("landing_page_url") or alert.get("landing_url"),
        "screenshot_url": alert.get("screenshot_url"),
        "security_url_count": len(security_urls),
        "security_urls_sample": "; ".join(security_urls[:3]),
        "has_security_urls": bool(security_urls),
        "geoedge_category": alert.get("geode_category") or alert.get("category"),
        "severity": alert.get("severity"),
        "malicious_type": alert.get("malicious_type"),
    }

    # Include the raw security urls as JSON list for completeness
    flattened["security_urls_all"] = security_urls
    return flattened


def fetch_alerts(args: argparse.Namespace) -> List[Dict[str, Any]]:
    client = GeoEdgeClient()
    now = datetime.utcnow()
    start = now - timedelta(days=args.days)

    alerts: List[Dict[str, Any]] = []
    chunk_index = 0
    for chunk_start, chunk_end in chunk_range(start, now, args.chunk_days):
        chunk_index += 1
        print(
            f"Chunk {chunk_index}: {chunk_start:%Y-%m-%d %H:%M} -> {chunk_end:%Y-%m-%d %H:%M}"
        )
        chunk_alerts = 0
        for alert in client.iter_alerts_history(
            min_datetime=chunk_start.strftime("%Y-%m-%d %H:%M:%S"),
            max_datetime=chunk_end.strftime("%Y-%m-%d %H:%M:%S"),
            full_raw=1,
            page_limit=5000,
            max_pages=args.max_pages,
        ):
            alerts.append(alert)
            chunk_alerts += 1
        print(
            f"  ↳ Retrieved {chunk_alerts} alerts for {chunk_start:%Y-%m-%d} to {chunk_end:%Y-%m-%d}"
        )
    return alerts


def build_output_path(user_path: Optional[str]) -> Path:
    if user_path:
        return Path(user_path).expanduser().resolve()
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return Path(f"geoedge_alerts_{timestamp}.xlsx").resolve()


def export_to_excel(alert_rows: List[Dict[str, Any]], output_path: Path) -> None:
    df = pd.DataFrame(alert_rows)
    if df.empty:
        raise RuntimeError("No alerts to export")

    df.sort_values("event_datetime", inplace=True)

    summary_alerts = (
        df.groupby("alert_name")
        .size()
        .reset_index(name="alert_count")
        .sort_values("alert_count", ascending=False)
    )

    summary_trigger = (
        df.groupby("trigger_metadata")
        .size()
        .reset_index(name="alert_count")
        .sort_values("alert_count", ascending=False)
    )

    summary_projects = (
        df.groupby(["project_id", "project_name"])
        .size()
        .reset_index(name="alert_count")
        .sort_values("alert_count", ascending=False)
    )

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Alerts", index=False)
        summary_alerts.to_excel(writer, sheet_name="By Alert Name", index=False)
        summary_trigger.to_excel(writer, sheet_name="By Trigger Metadata", index=False)
        summary_projects.to_excel(writer, sheet_name="By Project", index=False)

    print(f"Saved {len(df)} alerts to {output_path}")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    load_dotenv()

    print(
        f"Fetching GeoEdge alerts for last {args.days} days in {args.chunk_days}-day chunks (max_pages={args.max_pages})"
    )

    raw_alerts = fetch_alerts(args)
    print(f"Total alerts fetched: {len(raw_alerts)}")
    if not raw_alerts:
        return 0

    flattened = [flatten_alert(alert) for alert in raw_alerts]
    output_path = build_output_path(args.output)
    export_to_excel(flattened, output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
