"""Utility to verify GeoEdge alert coverage for a given date window.

This script walks the desired window in fixed-size chunks, counts how many alerts
GeoEdge returns for each chunk, and writes a JSON report describing coverage.
Use the JSON output to decide which chunks need to be refetched.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Tuple

from geoedge_projects.client import GeoEdgeClient


def parse_datetime(value: str) -> datetime:
    """Parse a YYYY-MM-DD (or ISO 8601) string into a timezone-aware datetime."""
    try:
        dt = datetime.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid date: {value}") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt


def chunk_window(
    start: datetime,
    end: datetime,
    chunk_days: int,
) -> Iterator[Tuple[datetime, datetime]]:
    if start >= end:
        return
    cursor = start
    delta = timedelta(days=max(1, chunk_days))
    while cursor < end:
        chunk_end = min(cursor + delta, end)
        yield cursor, chunk_end
        cursor = chunk_end


def collect_chunk_counts(
    *,
    start: datetime,
    end: datetime,
    chunk_days: int,
    page_limit: int,
    max_pages: Optional[int],
) -> List[Dict[str, object]]:
    client = GeoEdgeClient()
    chunk_id = 0
    results: List[Dict[str, object]] = []

    for chunk_start, chunk_end in chunk_window(start, end, chunk_days):
        chunk_id += 1
        alert_count = 0
        for _ in client.iter_alerts_history(
            min_datetime=chunk_start.strftime("%Y-%m-%d %H:%M:%S"),
            max_datetime=chunk_end.strftime("%Y-%m-%d %H:%M:%S"),
            full_raw=1,
            page_limit=page_limit,
            max_pages=max_pages,
        ):
            alert_count += 1
        results.append(
            {
                "chunk_id": chunk_id,
                "start": chunk_start.isoformat(),
                "end": chunk_end.isoformat(),
                "alerts": alert_count,
            }
        )
    return results


def main(argv: Optional[Iterable[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Verify GeoEdge alert coverage.")
    parser.add_argument("start", type=parse_datetime, help="Start date (YYYY-MM-DD or ISO)")
    parser.add_argument("end", type=parse_datetime, help="End date (exclusive)")
    parser.add_argument(
        "--chunk-days",
        type=int,
        default=15,
        help="Chunk size in days (default: 15)",
    )
    parser.add_argument(
        "--page-limit",
        type=int,
        default=5000,
        help="Alerts per API page (default: 5000)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Optional max pages per chunk (default: unlimited)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("alert_chunk_report.json"),
        help="Where to write the JSON report",
    )

    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.end <= args.start:
        parser.error("End must be after start")

    chunk_stats = collect_chunk_counts(
        start=args.start,
        end=args.end,
        chunk_days=args.chunk_days,
        page_limit=args.page_limit,
        max_pages=args.max_pages,
    )

    missing_chunks = [chunk for chunk in chunk_stats if chunk["alerts"] == 0]
    report = {
        "requested_start": args.start.isoformat(),
        "requested_end": args.end.isoformat(),
        "chunk_days": args.chunk_days,
        "total_chunks": len(chunk_stats),
        "total_alerts": sum(chunk["alerts"] for chunk in chunk_stats),
        "missing_chunks": missing_chunks,
        "chunk_stats": chunk_stats,
    }

    args.output.write_text(json.dumps(report, indent=2))
    print(f"Wrote {args.output} ({len(chunk_stats)} chunks, {len(missing_chunks)} missing)")


if __name__ == "__main__":  # pragma: no cover
    main()
