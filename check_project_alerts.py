#!/usr/bin/env python3
"""Check GeoEdge alerts for a list of projects."""

import argparse
import csv
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

from geoedge_projects.client import GeoEdgeClient


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch alert history for GeoEdge project IDs and summarize alert types.",
    )
    parser.add_argument(
        "--projects-file",
        type=Path,
        help="Path to a text file containing project IDs (one per line).",
    )
    parser.add_argument(
        "--projects",
        nargs="*",
        help="Project IDs provided directly on the command line.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Look back this many days for alerts (default: 30).",
    )
    parser.add_argument(
        "--min-datetime",
        help="Override the earliest UTC datetime (YYYY-MM-DD HH:MM:SS).",
    )
    parser.add_argument(
        "--max-datetime",
        help="Override the latest UTC datetime (YYYY-MM-DD HH:MM:SS).",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=500,
        help="Number of alerts to request per API page (1-10000).",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        help="Optional hard stop after this many pages per project.",
    )
    parser.add_argument(
        "--full-raw",
        action="store_true",
        help="Request the non-grouped (full_raw=1) alert history output.",
    )
    parser.add_argument(
        "--csv-output",
        type=Path,
        help="Optional path to write detailed alert rows as CSV.",
    )
    return parser.parse_args()


def load_project_ids(args: argparse.Namespace) -> List[str]:
    project_ids: List[str] = []

    if args.projects_file:
        try:
            text = args.projects_file.read_text(encoding="utf-8")
        except Exception as exc:
            raise RuntimeError(f"Could not read {args.projects_file}: {exc}") from exc
        for line in text.splitlines():
            cleaned = line.strip()
            if cleaned and not cleaned.startswith("#"):
                project_ids.append(cleaned)

    if args.projects:
        project_ids.extend(pid.strip() for pid in args.projects if pid.strip())

    if not project_ids:
        raise RuntimeError("No project IDs provided. Use --projects-file or --projects.")

    return sorted(set(project_ids))


def fmt(dt: Optional[str]) -> str:
    return dt or "N/A"


AlertDict = Dict[str, Any]


def extract_alert_labels(alert: AlertDict) -> List[str]:
    labels: List[str] = []
    alert_name = alert.get("alert_name")
    if alert_name:
        labels.append(str(alert_name))

    trigger_metadata = alert.get("trigger_metadata")
    if trigger_metadata:
        labels.append(str(trigger_metadata))

    details = alert.get("alert_details")
    if isinstance(details, dict):
        for key in list(details.keys()):
            key_str = str(key)
            if key in {"impact_string", "recommendation_string"}:
                continue
            labels.append(key_str.replace("_", " ").title())

    return sorted({label for label in labels if label})


def gather_alerts(
    client: GeoEdgeClient,
    project_id: str,
    min_datetime: Optional[str],
    max_datetime: Optional[str],
    full_raw: bool,
    page_size: int,
    max_pages: Optional[int],
) -> List[AlertDict]:
    alerts: List[AlertDict] = []
    for raw_alert in client.iter_alerts_history(
        project_id=project_id,
        min_datetime=min_datetime,
        max_datetime=max_datetime,
        full_raw=1 if full_raw else 0,
        page_limit=page_size,
        max_pages=max_pages,
    ):
        if isinstance(raw_alert, dict):
            alerts.append(dict(raw_alert))
    return alerts


def build_trigger_lookup(client: GeoEdgeClient) -> Dict[str, Dict[str, str]]:
    try:
        return client.list_alert_trigger_types()
    except Exception:
        return {}


def main() -> int:
    load_dotenv()
    args = parse_args()

    try:
        project_ids = load_project_ids(args)
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1

    min_dt = args.min_datetime
    max_dt = args.max_datetime

    if not min_dt:
        cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
        min_dt = cutoff.strftime("%Y-%m-%d %H:%M:%S")

    if not max_dt:
        now_utc = datetime.now(timezone.utc)
        max_dt = now_utc.strftime("%Y-%m-%d %H:%M:%S")

    try:
        client = GeoEdgeClient()
    except RuntimeError as exc:
        print(f"GeoEdge client error: {exc}", file=sys.stderr)
        return 1

    trigger_lookup = build_trigger_lookup(client)

    csv_rows: List[Dict[str, str]] = []

    print(
        f"Checking alerts for {len(project_ids)} project(s) between {fmt(min_dt)} and {fmt(max_dt)} (UTC)"
    )

    for project_id in project_ids:
        try:
            alerts = gather_alerts(
                client,
                project_id,
                min_dt,
                max_dt,
                full_raw=args.full_raw,
                page_size=args.page_size,
                max_pages=args.max_pages,
            )
        except Exception as exc:
            print(f"\nProject {project_id}: API error -> {exc}")
            continue

        if not alerts:
            print(f"\nProject {project_id}: no alerts found in range.")
            continue

        print(f"\nProject {project_id}: {len(alerts)} alert(s) found")
        for alert in alerts:
            trigger_id = str(alert.get("trigger_type_id")) if alert.get("trigger_type_id") else ""
            trigger_meta = trigger_lookup.get(trigger_id, {})
            trigger_name = trigger_meta.get("description") or trigger_meta.get("key") or "Unknown trigger"
            labels = extract_alert_labels(alert)
            label_text = ", ".join(labels) if labels else "(no additional labels)"
            event_time = fmt(alert.get("event_datetime"))
            alert_line = (
                f"  - {event_time} | Trigger: {trigger_name} (ID {trigger_id or 'n/a'}) | "
                f"Labels: {label_text}"
            )
            print(alert_line)
            if alert.get("alert_details_url"):
                print(f"    Details: {alert['alert_details_url']}")

            csv_rows.append(
                {
                    "project_id": project_id,
                    "history_id": str(alert.get("history_id", "")),
                    "event_datetime": event_time,
                    "trigger_type_id": trigger_id,
                    "trigger_key": trigger_meta.get("key", ""),
                    "trigger_description": trigger_meta.get("description", ""),
                    "alert_name": str(alert.get("alert_name", "")),
                    "trigger_metadata": str(alert.get("trigger_metadata", "")),
                    "labels": ";".join(labels),
                    "alert_details_url": str(alert.get("alert_details_url", "")),
                }
            )

    if args.csv_output and csv_rows:
        try:
            with args.csv_output.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "project_id",
                        "history_id",
                        "event_datetime",
                        "trigger_type_id",
                        "trigger_key",
                        "trigger_description",
                        "alert_name",
                        "trigger_metadata",
                        "labels",
                        "alert_details_url",
                    ],
                )
                writer.writeheader()
                writer.writerows(csv_rows)
            print(f"\nCSV report written to {args.csv_output}")
        except Exception as exc:
            print(f"Failed to write CSV report: {exc}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
