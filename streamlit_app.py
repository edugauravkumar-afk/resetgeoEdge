# pyright: ignore-all

import os
import re
import html
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Set, Tuple, cast

import pandas as pd
import pymysql
import streamlit as st
import vertica_python
from dotenv import load_dotenv

from geoedge_projects.client import GeoEdgeClient
from alert_chunk_tester import collect_chunk_counts as tester_collect_chunk_counts
from update_autoscan import geoedge_session, update_project_schedule as autoscan_update


load_dotenv()


ALERT_CACHE_DIR = Path(".cache")
ALERT_CACHE_FILE = ALERT_CACHE_DIR / "alert_history.pkl"


def ensure_cache_dir() -> None:
    if not ALERT_CACHE_DIR.exists():
        ALERT_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def chunked(items: Iterable[Any], size: int) -> Iterator[List[Any]]:
    """Yield successive fixed-size chunks from items."""
    chunk: List[Any] = []
    for item in items:
        chunk.append(item)
        if len(chunk) >= size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def chunk_datetime_range(
    end_time: datetime,
    days: int,
    chunk_days: int,
) -> Iterator[Tuple[datetime, datetime]]:
    """Generate [start, end) windows backwards from end_time."""
    start_time = end_time - timedelta(days=days)
    cursor = start_time
    chunk_delta = timedelta(days=max(1, chunk_days))
    while cursor < end_time:
        chunk_end = min(cursor + chunk_delta, end_time)
        yield cursor, chunk_end
        cursor = chunk_end


def chunk_datetime_window(
    start_time: datetime,
    end_time: datetime,
    chunk_days: int,
) -> Iterator[Tuple[datetime, datetime]]:
    """Generate [start, end) windows for arbitrary start/end times."""
    cursor = start_time
    if cursor >= end_time:
        return
    chunk_delta = timedelta(days=max(1, chunk_days))
    while cursor < end_time:
        chunk_end = min(cursor + chunk_delta, end_time)
        yield cursor, chunk_end
        cursor = chunk_end


def parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def build_backend_chunk_report(
    start_dt: datetime,
    end_dt: datetime,
    *,
    chunk_days: int,
    page_limit: int,
    max_pages: Optional[int],
) -> Dict[str, Any]:
    start_utc = normalize_utc(start_dt)
    end_utc = normalize_utc(end_dt)
    if start_utc >= end_utc:
        raise ValueError("Start must be before end for chunk scan")

    chunk_stats: List[Dict[str, Any]] = tester_collect_chunk_counts(
        start=start_utc,
        end=end_utc,
        chunk_days=max(1, int(chunk_days)),
        page_limit=max(1, min(int(page_limit), 10000)),
        max_pages=int(max_pages) if max_pages not in (None, 0) else None,
    )

    def _coerce_alerts(value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):  # pragma: no cover - defensive
            return 0

    missing = [chunk for chunk in chunk_stats if _coerce_alerts(chunk.get("alerts")) == 0]
    total_alerts = sum(_coerce_alerts(chunk.get("alerts")) for chunk in chunk_stats)

    return {
        "requested_start": start_utc.isoformat(),
        "requested_end": end_utc.isoformat(),
        "chunk_days": int(chunk_days),
        "page_limit": int(page_limit),
        "max_pages": int(max_pages) if max_pages else None,
        "total_chunks": len(chunk_stats),
        "total_alerts": total_alerts,
        "missing_chunks": missing,
        "chunk_stats": chunk_stats,
    }


def resolve_alert_range(
    choice: str,
    custom_start: Optional[date],
    custom_end: Optional[date],
) -> Dict[str, Any]:
    presets = {
        "Last 7 days": 7,
        "Last 30 days": 30,
        "Last 60 days": 60,
        "Last 90 days": 90,
    }

    now_utc = datetime.now(timezone.utc)

    if choice in presets:
        days = presets[choice]
        end_dt = now_utc
        start_dt = end_dt - timedelta(days=days)
        label = choice
    else:
        fallback_start = date.today() - timedelta(days=30)
        fallback_end = date.today()
        start_date = custom_start or fallback_start
        end_date = custom_end or fallback_end
        if start_date > end_date:
            start_date, end_date = end_date, start_date
        start_dt = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        # include full end_date by adding a day
        end_dt = datetime.combine(end_date + timedelta(days=1), datetime.min.time()).replace(tzinfo=timezone.utc)
        days = max(1, (end_dt - start_dt).days)
        label = f"{start_date:%d %b %Y} → {end_date:%d %b %Y}"

    return {
        "label": label,
        "start": normalize_utc(start_dt),
        "end": normalize_utc(end_dt),
        "days": max(1, days),
    }


def load_alert_cache() -> pd.DataFrame:
    if ALERT_CACHE_FILE.exists():
        try:
            return pd.read_pickle(ALERT_CACHE_FILE)
        except Exception:
            return pd.DataFrame()  # Return empty DataFrame on exception
    return pd.DataFrame()  # Return empty DataFrame if file does not exist


def save_alert_cache(df: pd.DataFrame) -> None:
    try:
        ensure_cache_dir()
        df.to_pickle(ALERT_CACHE_FILE)
    except Exception as exc:
        st.warning(f"Failed to persist alert cache: {exc}")  # Log warning on failure


def clear_alert_cache() -> None:
    try:
        if ALERT_CACHE_FILE.exists():
            ALERT_CACHE_FILE.unlink()
    except Exception as exc:
        st.warning(f"Failed to delete alert cache: {exc}")


def extract_project(alert: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    mapping = alert.get("project_name")
    project_map: Dict[str, Any] = cast(Dict[str, Any], mapping) if isinstance(mapping, dict) else {}
    if project_map:
        project_id, project_name = next(iter(project_map.items()))
        return str(project_id), str(project_name)
    return None, None


def extract_location(alert: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    mapping = alert.get("location")
    location_map: Dict[str, Any] = cast(Dict[str, Any], mapping) if isinstance(mapping, dict) else {}
    if location_map:
        location_code, location_name = next(iter(location_map.items()))
        return str(location_code), str(location_name)
    return None, None


def guess_campaign_id(project_name: Optional[str]) -> Optional[str]:
    if not project_name:
        return None
    match = re.search(r"(\d{5,})", project_name)
    if match:
        return match.group(1)
    return None


def flatten_alert_payload(alert: Dict[str, Any]) -> Dict[str, Any]:
    project_id, project_name = extract_project(alert)
    location_code, location_name = extract_location(alert)
    trigger_metadata = alert.get("trigger_metadata")
    if not isinstance(trigger_metadata, dict):
        trigger_metadata = {}

    alert_details = alert.get("alert_details")
    if not isinstance(alert_details, dict):
        alert_details = {}

    screenshot_url = (
        alert_details.get("screenshot_url")
        or alert.get("screenshot_url")
        or alert.get("screenshot")
    )
    details_url = alert_details.get("alert_details_url") or alert.get("alert_details_url")

    return {
        "alert_id": str(alert.get("alert_id") or alert.get("id") or ""),
        "history_id": str(alert.get("history_id") or ""),
        "event_datetime": alert.get("event_datetime") or alert.get("created"),
        "alert_name": alert.get("alert_name") or alert.get("trigger_name") or "",
        "severity": alert.get("severity") or alert_details.get("severity") or "",
        "malicious_type": alert.get("malicious_type") or alert_details.get("type") or "",
        "security_url_count": alert.get("security_url_count") or alert_details.get("url_count"),
        "project_id": project_id or str(alert.get("project_id") or ""),
        "project_name": project_name or str(alert.get("project_display_name") or ""),
        "campaign_id_guess": guess_campaign_id(project_name or alert.get("project_display_name")),
        "location_code": location_code or alert.get("location_code"),
        "location_name": location_name or alert.get("location_name"),
        "trigger_metadata": trigger_metadata,
        "alert_details": alert_details,
        "alert_details_url": details_url,
        "screenshot_url": screenshot_url,
        "raw_alert": alert,
    }


def fetch_alert_history(
    days: int,
    chunk_days: int,
    max_pages: Optional[int],
    start_datetime: Optional[datetime] = None,
    end_datetime: Optional[datetime] = None,
    force_full_scan: bool = False,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Return alert history using a local cache and only fetch missing windows."""

    ensure_cache_dir()
    client = GeoEdgeClient()
    now_utc = datetime.now(timezone.utc)
    desired_end = normalize_utc(end_datetime) if end_datetime else now_utc
    desired_start = normalize_utc(start_datetime) if start_datetime else desired_end - timedelta(days=days)
    if desired_start >= desired_end:
        desired_start = desired_end - timedelta(days=max(1, days))
    desired_window_days = max(1, int((desired_end - desired_start).days) or 1)

    cached_df = load_alert_cache()
    chunk_counter = 0

    if not cached_df.empty:
        cached_df["_event_dt"] = pd.to_datetime(cached_df["event_datetime"], errors="coerce", utc=True)
        cached_df = cached_df.dropna(subset=["_event_dt"])
        cached_df.sort_values("_event_dt", inplace=True)
        cached_start = cached_df["_event_dt"].min()
        cached_end = cached_df["_event_dt"].max()
    else:
        cached_start = None
        cached_end = None

    if force_full_scan:
        missing_ranges: List[Tuple[datetime, datetime]] = [(desired_start, desired_end)]
    else:
        missing_ranges = []
        if cached_start is None or cached_end is None or cached_end < desired_start:
            cached_df = pd.DataFrame()
            missing_ranges.append((desired_start, desired_end))
        else:
            if desired_start < cached_start:
                missing_ranges.append((desired_start, cached_start))
            if cached_end < desired_end:
                missing_ranges.append((cached_end, desired_end))

    new_alert_rows: List[Dict[str, Any]] = []
    chunk_stats: List[Dict[str, Any]] = []
    for range_start, range_end in missing_ranges:
        if range_end <= range_start:
            continue
        for chunk_start, chunk_end in chunk_datetime_window(range_start, range_end, chunk_days):
            chunk_counter += 1
            chunk_total = 0
            for alert in client.iter_alerts_history(
                min_datetime=chunk_start.strftime("%Y-%m-%d %H:%M:%S"),
                max_datetime=chunk_end.strftime("%Y-%m-%d %H:%M:%S"),
                full_raw=1,
                page_limit=5000,
                max_pages=max_pages,
            ):
                new_alert_rows.append(alert)
                chunk_total += 1
            chunk_stats.append(
                {
                    "chunk_id": chunk_counter,
                    "start": chunk_start.isoformat(),
                    "end": chunk_end.isoformat(),
                    "alerts": chunk_total,
                }
            )

    new_df = pd.DataFrame([flatten_alert_payload(alert) for alert in new_alert_rows]) if new_alert_rows else pd.DataFrame()
    if not new_df.empty:
        new_df["_event_dt"] = pd.to_datetime(new_df["event_datetime"], errors="coerce", utc=True)
        if cached_df.empty:
            combined_df = new_df.copy()
        else:
            combined_df = pd.concat([cached_df, new_df], ignore_index=True)
    else:
        combined_df = cached_df.copy()

    if combined_df.empty:
        metadata = {
            "chunks": chunk_counter,
            "fetched": 0,
            "window_start": desired_start.isoformat(),
            "window_end": desired_end.isoformat(),
            "desired_window_start": desired_start.isoformat(),
            "desired_window_end": desired_end.isoformat(),
            "cache_used": False,
            "ranges_fetched": len(missing_ranges),
            "days_requested": desired_window_days,
            "full_scan": force_full_scan,
            "chunk_stats": chunk_stats,
        }
        if "_event_dt" in combined_df.columns:
            combined_df = combined_df.drop(columns=["_event_dt"])
        save_alert_cache(combined_df)
        return combined_df, metadata

    if "_event_dt" not in combined_df.columns:
        combined_df["_event_dt"] = pd.to_datetime(combined_df["event_datetime"], errors="coerce", utc=True)

    combined_df = combined_df.dropna(subset=["_event_dt"])

    def build_dedupe_key(row: pd.Series) -> str:
        history_id = str(row.get("history_id") or "").strip()
        if history_id:
            return history_id
        alert_id = str(row.get("alert_id") or "").strip()
        event_dt = str(row.get("event_datetime") or "").strip()
        project_id = str(row.get("project_id") or "").strip()
        location_code = str(row.get("location_code") or "").strip()
        return "|".join([alert_id, event_dt, project_id, location_code])

    combined_df["_dedupe_key"] = combined_df.apply(build_dedupe_key, axis=1)
    combined_df.sort_values("_event_dt", ascending=False, inplace=True)
    combined_df = combined_df.drop_duplicates(subset=["_dedupe_key"], keep="first")
    combined_df.drop(columns=["_dedupe_key"], inplace=True)
    cache_df = combined_df.copy()

    recent_mask = (combined_df["_event_dt"] >= desired_start) & (combined_df["_event_dt"] <= desired_end)
    filtered_df = combined_df[recent_mask].copy()

    if filtered_df.empty:
        filtered_df = filtered_df.drop(columns=["_event_dt"])
        cache_df = cache_df.drop(columns=["_event_dt"])
        save_alert_cache(cache_df)
        metadata = {
            "chunks": chunk_counter,
            "fetched": 0,
            "window_start": desired_start.isoformat(),
            "window_end": desired_end.isoformat(),
            "desired_window_start": desired_start.isoformat(),
            "desired_window_end": desired_end.isoformat(),
            "cache_used": False,
            "ranges_fetched": len(missing_ranges),
            "days_requested": desired_window_days,
            "full_scan": force_full_scan,
            "chunk_stats": chunk_stats,
        }
        return filtered_df, metadata

    actual_start = filtered_df["_event_dt"].min()
    actual_end = filtered_df["_event_dt"].max()

    filtered_df.drop(columns=["_event_dt"], inplace=True)
    cache_df.drop(columns=["_event_dt"], inplace=True)
    save_alert_cache(cache_df)

    metadata = {
        "chunks": chunk_counter,
        "fetched": len(filtered_df),
        "window_start": (actual_start or desired_start).isoformat(),
        "window_end": (actual_end or desired_end).isoformat(),
        "desired_window_start": desired_start.isoformat(),
        "desired_window_end": desired_end.isoformat(),
        "cache_used": not bool(missing_ranges),
        "ranges_fetched": len(missing_ranges),
        "days_requested": desired_window_days,
        "full_scan": force_full_scan,
        "chunk_stats": chunk_stats,
    }
    return filtered_df, metadata


def fetch_campaign_accounts(db_choice: str, campaign_ids: Iterable[Any]) -> Dict[int, str]:
    """Return mapping of campaign id to account (syndicator) id."""
    unique_ids = sorted({int(str(cid)) for cid in campaign_ids if str(cid).strip()})
    if not unique_ids:
        return {}

    results: Dict[int, str] = {}

    if db_choice == "mysql":
        host = os.getenv("MYSQL_HOST")
        port = int(os.getenv("MYSQL_PORT", "3306"))
        user = os.getenv("MYSQL_USER")
        password = os.getenv("MYSQL_PASSWORD")
        db = os.getenv("MYSQL_DB")

        if not (host and user and password and db):
            return {}

        conn: Optional[pymysql.connections.Connection] = None
        try:
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
            with conn.cursor() as cur:
                for chunk in chunked(unique_ids, 500):
                    placeholders = ",".join(["%s"] * len(chunk))
                    sql = f"SELECT id, syndicator_id FROM trc.sp_campaigns WHERE id IN ({placeholders})"
                    cur.execute(sql, tuple(chunk))
                    for campaign_id, account_id in cur.fetchall():
                        if campaign_id is not None and account_id is not None:
                            results[int(campaign_id)] = str(account_id)
        except Exception as error:
            st.warning(f"Failed to fetch campaign accounts: {error}")
        finally:
            if conn is not None:
                conn.close()
    else:
        host = os.getenv("VERTICA_HOST")
        port = int(os.getenv("VERTICA_PORT", "5433"))
        user = os.getenv("VERTICA_USER")
        password = os.getenv("VERTICA_PASSWORD")
        db = os.getenv("VERTICA_DB")

        if not (host and user and password and db):
            return {}

        conn_info: Dict[str, Any] = {
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
        try:
            with vertica_python.connect(**conn_info) as connection:
                with connection.cursor() as cur:
                    for chunk in chunked(unique_ids, 500):
                        placeholders = ",".join(["%s"] * len(chunk))
                        sql = f"SELECT id, syndicator_id FROM trc.sp_campaigns WHERE id IN ({placeholders})"
                        cur.execute(sql, tuple(chunk))
                        for campaign_id, account_id in cur.fetchall():
                            if campaign_id is not None and account_id is not None:
                                results[int(campaign_id)] = str(account_id)
        except Exception as error:
            st.warning(f"Failed to fetch campaign accounts: {error}")

    return results


def summarize_recent_alerts(
    client: GeoEdgeClient,
    project_id: str,
    *,
    trigger_lookup: Optional[Dict[str, Dict[str, str]]] = None,
    days: int = 30,
    preview_limit: int = 3,
    max_items: int = 250,
) -> str:
    """Return short alert summary for a project within the last N days."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    lookup = trigger_lookup or {}
    total_found = 0
    preview: List[str] = []

    def extract_topics(alert: Dict[str, Any]) -> List[str]:
        topics: Set[str] = set()

        metadata = alert.get("trigger_metadata")
        if isinstance(metadata, dict):
            topics.update(str(value).strip() for value in metadata.values() if value)
        elif metadata:
            topics.add(str(metadata).strip())

        details = alert.get("alert_details")
        if isinstance(details, dict):
            for key, value in details.items():
                key_lower = str(key).lower()
                if key_lower in {"impact_string", "recommendation_string"}:
                    continue

                def add_values(item: Any) -> None:
                    if isinstance(item, dict):
                        for sub_val in item.values():
                            add_values(sub_val)
                    elif isinstance(item, (list, tuple, set)):
                        for sub_val in item:
                            add_values(sub_val)
                    else:
                        text = str(item).strip()
                        if text:
                            topics.add(text)

                if any(token in key_lower for token in {"category", "type", "violation", "reason", "classification", "issue"}):
                    add_values(value)
                elif isinstance(value, (dict, list, tuple, set)):
                    add_values(value)
                else:
                    text = str(value).strip()
                    if text and len(text) <= 80:
                        topics.add(text)

        return sorted(topic for topic in topics if topic)

    try:
        for alert in client.iter_alerts_history(
            project_id=project_id,
            min_datetime=cutoff,
            page_limit=min(max_items, 500),
            max_pages=max(1, (max_items // 500) + 1),
        ):
            if not isinstance(alert, dict):
                continue
            total_found += 1
            if len(preview) < preview_limit:
                trigger_id = str(alert.get("trigger_type_id") or "").strip()
                trigger_meta = lookup.get(trigger_id, {})
                trigger_name = (
                    trigger_meta.get("description")
                    or trigger_meta.get("key")
                    or str(alert.get("alert_name") or "Unknown trigger")
                )
                alert_name = str(alert.get("alert_name") or "").strip()
                event_time = str(alert.get("event_datetime") or alert.get("created") or "n/a")
                parts = [event_time]
                if alert_name:
                    parts.append(alert_name)
                parts.append(trigger_name)
                topics = extract_topics(alert)
                if topics:
                    parts.append(", ".join(topics))
                preview.append(" · ".join(parts))
            if total_found >= max_items:
                break
    except Exception as exc:  # pragma: no cover - network errors
        return f"alerts error: {exc}"

    if total_found == 0:
        return f"alerts: none in last {days} days"

    visible = "; ".join(preview)
    if total_found > preview_limit:
        return f"alerts: {total_found} (latest {visible})"

    return f"alerts: {total_found} ({visible})"
    

def extract_status(response: Any) -> Tuple[str, str]:
    """Return status code/message tuple from a GeoEdge API response."""
    if not isinstance(response, dict):
        return "", ""
    status = response.get("status")
    if isinstance(status, dict):
        code = status.get("code")
        message = status.get("message")
        return str(code or ""), str(message or "")
    return "", ""


def is_success(code: str, message: str) -> bool:
    """Determine whether a GeoEdge status payload represents success."""
    markers = {"ok", "success", "updated"}
    code_norm = (code or "").strip().lower()
    message_norm = (message or "").strip().lower()
    if not code_norm and not message_norm:
        return True
    if code_norm in markers:
        return True
    return any(marker in message_norm for marker in markers if message_norm)


def apply_zero_schedule(project_ids: Iterable[str]) -> List[Tuple[str, str]]:
    """Disable auto_scan for the provided projects and summarize recent alerts."""
    ids = [str(pid).strip() for pid in project_ids if str(pid).strip()]
    if not ids:
        return []

    try:
        session = geoedge_session()
    except Exception as exc:
        return [(pid, f"ERROR creating GeoEdge session: {exc}") for pid in ids]

    try:
        geo_client = GeoEdgeClient()
    except Exception as exc:
        return [(pid, f"ERROR creating GeoEdge client: {exc}") for pid in ids]

    try:
        trigger_lookup = geo_client.list_alert_trigger_types()
    except Exception:
        trigger_lookup = {}

    alerts_cache: Dict[str, str] = {}
    results: List[Tuple[str, str]] = []

    for pid in ids:
        try:
            project = geo_client.get_project(pid)
        except Exception:
            project = {}

        current_auto = project.get("auto_scan")
        current_times = project.get("times_per_day")
        current_auto_int: Optional[int] = None
        try:
            if current_auto is not None:
                current_auto_int = int(current_auto)
        except (TypeError, ValueError):
            current_auto_int = None

        alerts_text = alerts_cache.get(pid)
        if alerts_text is None:
            alerts_text = summarize_recent_alerts(
                geo_client,
                pid,
                trigger_lookup=trigger_lookup,
            )
            alerts_cache[pid] = alerts_text

        if current_auto_int == 0:
            note = "Already disabled"
            if current_times is not None:
                note = f"Already disabled (times_per_day={current_times})"
            results.append((pid, f"{note}. {alerts_text}"))
            continue

        try:
            response_auto = autoscan_update(session, pid, auto=0, times=None, dry_run=False)
        except Exception as update_exc:
            results.append((pid, f"ERROR updating auto_scan: {update_exc}"))
            continue

        auto_code, auto_message = extract_status(response_auto)
        if not is_success(auto_code, auto_message):
            message = auto_message or auto_code or "Unknown error"
            if "times_per_day" in message.lower():
                message = "GeoEdge requires times_per_day to stay at an allowed value; auto_scan disabled only."
            results.append((pid, f"ERROR updating auto_scan: {message}"))
            continue

        try:
            refreshed = geo_client.get_project(pid)
        except Exception:
            refreshed = {}

        final_auto = refreshed.get("auto_scan", "unknown")
        final_times = refreshed.get("times_per_day", "unknown")

        alerts_text = alerts_cache.get(pid) or summarize_recent_alerts(
            geo_client,
            pid,
            trigger_lookup=trigger_lookup,
        )
        alerts_cache[pid] = alerts_text

        results.append(
            (
                pid,
                f"auto_scan={final_auto}, times_per_day={final_times}; {alerts_text}",
            )
        )

    return results


def get_total_count(
    db_choice: str,
    days: int,
    regex: Optional[str],
    *,
    specific_date: Optional[str] = None,
    project_ids: Optional[Set[str]] = None,
) -> int:
    """Get total count of matching records without limit."""

    if db_choice == "mysql":
        host = os.getenv("MYSQL_HOST")
        port = int(os.getenv("MYSQL_PORT", "3306"))
        user = os.getenv("MYSQL_USER")
        password = os.getenv("MYSQL_PASSWORD")
        db = os.getenv("MYSQL_DB")

        if not (host and user and password and db):
            return 0

        conn: Optional[pymysql.connections.Connection] = None
        try:
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
            with conn.cursor() as cur:
                conditions = ["sii.instruction_status = 'ACTIVE'"]
                params: List[Any] = []

                if project_ids:
                    project_list = sorted(project_ids)
                    placeholders = ",".join(["%s"] * len(project_list))
                    conditions.append(f"p.project_id IN ({placeholders})")
                    params.extend(project_list)
                else:
                    if specific_date:
                        conditions.append("DATE(p.creation_date) = %s")
                        params.append(specific_date)
                    else:
                        conditions.append("p.creation_date >= DATE_SUB(NOW(), INTERVAL %s DAY)")
                        params.append(days)

                    if regex:
                        conditions.append("CONCAT(',', REPLACE(COALESCE(p.locations, ''), ' ', ''), ',') REGEXP %s")
                        params.append(regex)

                where_clause = " AND ".join(conditions)
                sql = f"""
                    SELECT COUNT(DISTINCT p.project_id)
                    FROM trc.geo_edge_projects AS p
                    JOIN trc.sp_campaign_inventory_instructions sii ON p.campaign_id = sii.campaign_id
                    WHERE {where_clause}
                """
                cur.execute(sql, tuple(params))
                result = cur.fetchone()
                return int(result[0]) if result else 0
        except Exception:
            return 0
        finally:
            if conn is not None:
                conn.close()

    else:
        host = os.getenv("VERTICA_HOST")
        port = int(os.getenv("VERTICA_PORT", "5433"))
        user = os.getenv("VERTICA_USER")
        password = os.getenv("VERTICA_PASSWORD")
        db = os.getenv("VERTICA_DB")

        if not (host and user and password and db):
            return 0

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

        try:
            with vertica_python.connect(**conn_info) as connection:
                with connection.cursor() as cur:
                    conditions = ["sii.instruction_status = 'ACTIVE'"]
                    params: List[Any] = []

                    if project_ids:
                        project_list = sorted(project_ids)
                        placeholders = ",".join(["%s"] * len(project_list))
                        conditions.append(f"p.project_id IN ({placeholders})")
                        params.extend(project_list)
                    else:
                        if specific_date:
                            conditions.append("DATE(p.creation_date) = %s")
                            params.append(specific_date)
                        else:
                            conditions.append(f"p.creation_date >= NOW() - INTERVAL '{days} DAYS'")

                        if regex:
                            conditions.append("REGEXP_LIKE(',' || REPLACE(COALESCE(p.locations, ''), ' ', '') || ',', %s)")
                            params.append(regex)

                    where_clause = " AND ".join(conditions)
                    sql = f"""
                        SELECT COUNT(DISTINCT p.project_id)
                        FROM trc.geo_edge_projects AS p
                        JOIN trc.sp_campaign_inventory_instructions sii ON p.campaign_id = sii.campaign_id
                        WHERE {where_clause}
                    """
                    cur.execute(sql, tuple(params))
                    result = cur.fetchone()
                    return int(result[0]) if result else 0
        except Exception:
            return 0

    return 0


def query_mysql(
    days: int,
    regex: Optional[str],
    limit: int,
    *,
    specific_date: Optional[str] = None,
    project_ids: Optional[Set[str]] = None,
) -> List[Tuple[Any, ...]]:
    """Query MySQL database for projects"""
    host = os.getenv("MYSQL_HOST")
    port = int(os.getenv("MYSQL_PORT", "3306"))
    user = os.getenv("MYSQL_USER")
    password = os.getenv("MYSQL_PASSWORD")
    db = os.getenv("MYSQL_DB")
    auth_plugin = os.getenv("MYSQL_AUTH_PLUGIN") or "mysql_native_password"

    if not (host and user and password and db):
        st.error("Missing MySQL environment variables")
        return []

    try:
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
        
        with conn.cursor() as cur:
            conditions = ["sii.instruction_status = 'ACTIVE'"]
            params: List[Any] = []

            if project_ids:
                project_id_list = sorted(project_ids)
                placeholders = ",".join(["%s"] * len(project_id_list))
                conditions.append(f"p.project_id IN ({placeholders})")
                params.extend(project_id_list)
            else:
                if specific_date:
                    conditions.append("DATE(p.creation_date) = %s")
                    params.append(specific_date)
                else:
                    conditions.append("p.creation_date >= DATE_SUB(NOW(), INTERVAL %s DAY)")
                    params.append(days)

                if regex:
                    conditions.append("CONCAT(',', REPLACE(COALESCE(p.locations, ''), ' ', ''), ',') REGEXP %s")
                    params.append(regex)

            where_clause = " AND ".join(conditions)
            sql = f"""
                SELECT DISTINCT
                    p.project_id,
                    p.campaign_id,
                    p.locations,
                    p.creation_date,
                    sii.instruction_status
                FROM trc.geo_edge_projects AS p
                JOIN trc.sp_campaign_inventory_instructions sii ON p.campaign_id = sii.campaign_id
                WHERE {where_clause}
                ORDER BY p.creation_date DESC
                LIMIT {int(limit)}
            """
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()
            return list(rows)
    except Exception as e:
        st.error(f"Database query failed: {e}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()

def query_vertica(
    days: int,
    regex: Optional[str],
    limit: int,
    *,
    specific_date: Optional[str] = None,
    project_ids: Optional[Set[str]] = None,
) -> List[Tuple[Any, ...]]:
    """Query Vertica database for projects."""
    host = os.getenv("VERTICA_HOST")
    port = int(os.getenv("VERTICA_PORT", "5433"))
    user = os.getenv("VERTICA_USER")
    password = os.getenv("VERTICA_PASSWORD")
    db = os.getenv("VERTICA_DB")

    if not (host and user and password and db):
        st.error("Missing Vertica environment variables")
        return []

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

    try:
        with vertica_python.connect(**conn_info) as connection:
            with connection.cursor() as cur:
                conditions = ["sii.instruction_status = 'ACTIVE'"]
                params: List[Any] = []

                if project_ids:
                    project_id_list = sorted(project_ids)
                    placeholders = ",".join(["%s"] * len(project_id_list))
                    conditions.append(f"p.project_id IN ({placeholders})")
                    params.extend(project_id_list)
                else:
                    if specific_date:
                        conditions.append("DATE(p.creation_date) = %s")
                        params.append(specific_date)
                    else:
                        conditions.append(f"p.creation_date >= NOW() - INTERVAL '{days} DAYS'")

                    if regex:
                        conditions.append(
                            "REGEXP_LIKE(',' || REPLACE(COALESCE(p.locations, ''), ' ', '') || ',', %s)"
                        )
                        params.append(regex)

                where_clause = " AND ".join(conditions)
                sql = f"""
                    SELECT DISTINCT
                        p.project_id,
                        p.campaign_id,
                        p.locations,
                        p.creation_date,
                        sii.instruction_status
                    FROM trc.geo_edge_projects AS p
                    JOIN trc.sp_campaign_inventory_instructions sii ON p.campaign_id = sii.campaign_id
                    WHERE {where_clause}
                    ORDER BY p.creation_date DESC
                    LIMIT {int(limit)}
                """
                cur.execute(sql, tuple(params))
                rows = cur.fetchall()
                return list(rows)
    except Exception as error:
        st.error(f"Database query failed: {error}")
        return []

@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_project_details(project_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """Fetch auto_scan and times_per_day details from GeoEdge API."""
    if not project_ids:
        return {}
    
    try:
        client = GeoEdgeClient()
        project_details: Dict[str, Dict[str, Any]] = {}
        
        # Create a progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, project_id in enumerate(project_ids):
            try:
                status_text.text(f"Fetching project details... {i+1}/{len(project_ids)}")
                progress_bar.progress((i + 1) / len(project_ids))
                
                raw_project: Any = client.get_project(project_id)
                project_data = cast(Dict[str, Any], raw_project or {})
                project_details[project_id] = {
                    "auto_scan": project_data.get("auto_scan", "N/A"),
                    "times_per_day": project_data.get("times_per_day", "N/A"),
                }
            except Exception as e:
                st.warning(f"Could not fetch details for project {project_id}: {e}")
                project_details[project_id] = {
                    "auto_scan": "Error",
                    "times_per_day": "Error",
                }
        
        # Clear progress indicators
        progress_bar.empty()
        status_text.empty()
        
        return project_details
    except Exception as e:
        st.error(f"Could not initialize GeoEdge client: {e}")
        return {pid: {"auto_scan": "API_Error", "times_per_day": "API_Error"} for pid in project_ids}


def stringify_locations(raw_locations: Any) -> str:
    """Convert GeoEdge locations payload into a comma-separated code list."""
    if isinstance(raw_locations, dict):
        codes = []
        for key, value in raw_locations.items():
            if isinstance(value, dict):
                candidate = value.get("id") or value.get("code") or value.get("name") or key
                if candidate:
                    codes.append(str(candidate).strip().upper())
            elif isinstance(value, (bool, int)):
                if value:
                    codes.append(str(key).strip().upper())
            else:
                codes.append(str(key).strip().upper())
        return ", ".join(sorted({code for code in codes if code}))

    if isinstance(raw_locations, list):
        codes = []
        for entry in raw_locations:
            if isinstance(entry, dict):
                candidate = entry.get("id") or entry.get("code") or entry.get("name")
                if candidate:
                    codes.append(str(candidate).strip().upper())
            elif entry:
                codes.append(str(entry).strip().upper())
        return ", ".join(sorted({code for code in codes if code}))

    if isinstance(raw_locations, str):
        return raw_locations

    return ""


def fetch_account_statuses(db_choice: str, account_ids: Iterable[Any]) -> Dict[str, str]:
    """Fetch account freeze statuses using the credit/pausing query."""
    unique_ids = sorted({int(str(acc)) for acc in account_ids if str(acc).strip().isdigit()})
    if not unique_ids:
        return {}

    results: Dict[str, str] = {}

    sql_template = """
        WITH accounts_temp AS (
            SELECT 'Network' AS account_type,
                   n.network_id AS account_id,
                   n.monthly_credit_limit,
                   n.total_credit_limit,
                   n.ccb_billing_cycle,
                   n.is_depleted,
                   n.is_paused
            FROM trc.sp_network_syndication n
            WHERE n.network_id IN (
                SELECT id FROM trc.publishers WHERE type = 'NETWORK'
            )
            AND n.network_id IN ({placeholders})
            UNION ALL
            SELECT 'Syndicator' AS account_type,
                   sb.syndicator_id AS account_id,
                   sv.monthly_credit_limit,
                   sb.total_credit_limit,
                   sb.ccb_billing_cycle,
                   sb.is_depleted,
                   sv.is_paused
            FROM trc.sp_syndication_base sb
                     LEFT JOIN trc.sp_syndication_v2 sv ON sb.syndicator_id = sv.syndicator_id
            WHERE sv.syndicator_id IN (
                SELECT id FROM trc.publishers WHERE type = 'GENERAL'
            )
              AND sv.campaign_type = 'SPONSORED'
              AND sb.campaign_type = 'SPONSORED'
              AND sb.syndicator_id IN ({placeholders})
        ),
        main_data AS (
            SELECT a.account_id,
                   c.description AS account_name,
                   a.account_type,
                   c.status AS publisher_status,
                   a.is_depleted,
                   a.is_paused
            FROM accounts_temp a
                     LEFT JOIN trc.publishers c ON c.id = a.account_id
        )
        SELECT account_id,
               CASE
                   WHEN publisher_status != 'LIVE'
                       THEN 'Frozen - Account is inactive'
                   WHEN is_paused = 1
                       THEN 'Frozen - Account is manually paused'
                   WHEN is_depleted = 1
                       THEN 'Frozen - Account depleted (credit used up)'
                   ELSE 'Active'
               END AS freeze_status
        FROM main_data
        WHERE account_id IN ({placeholders})
    """

    placeholders = ", ".join(["%s"] * len(unique_ids))
    formatted_sql = sql_template.format(placeholders=placeholders)
    params: List[Any] = list(unique_ids) * 3

    connection = None
    try:
        if db_choice == "mysql":
            host = os.getenv("MYSQL_HOST") or ""
            port = int(os.getenv("MYSQL_PORT", "3306"))
            user = os.getenv("MYSQL_USER") or ""
            password = os.getenv("MYSQL_PASSWORD") or ""
            db = os.getenv("MYSQL_DB") or ""

            connection = pymysql.connect(
                host=host,
                user=user,
                password=password,
                database=db,
                port=port,
                cursorclass=pymysql.cursors.Cursor,
            )
        elif db_choice == "vertica":
            host = os.getenv("VERTICA_HOST") or ""
            user = os.getenv("VERTICA_USER") or ""
            password = os.getenv("VERTICA_PASSWORD") or ""
            database = os.getenv("VERTICA_DB") or ""
            port = int(os.getenv("VERTICA_PORT", "5433"))

            connection = vertica_python.connect(
                host=host,
                user=user,
                password=password,
                database=database,
                port=port,
                autocommit=True,
            )
        else:  # pragma: no cover - guarded by selectbox
            st.error(f"Unsupported database choice: {db_choice}")
            return results

        with connection.cursor() as cursor:  # type: ignore[union-attr]
            cursor.execute(formatted_sql, params)
            for account_id, freeze_status in cursor.fetchall():
                results[str(account_id)] = str(freeze_status)

    except Exception as error:
        st.warning(f"Failed to fetch account statuses: {error}")
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass

    return results


def build_regex(countries_csv: str) -> Optional[str]:
    """Build a comma-safe regex pattern for country filtering."""
    tokens = [token.strip().upper() for token in countries_csv.split(",") if token.strip()]
    if not tokens:
        return None
    pattern = ",(" + "|".join(sorted(set(tokens))) + "),"
    return pattern


def parse_project_ids(raw: str) -> Set[str]:
    """Parse user-supplied project ids (comma, space, or newline separated)."""
    if not raw:
        return set()
    ids: Set[str] = set()
    for token in re.split(r"[\s,]+", raw):
        token = token.strip()
        if token:
            ids.add(token)
    return ids


def build_oct21_dataframe() -> Tuple[pd.DataFrame, List[Tuple[str, str]]]:
    """Return Oct 21 remediation projects plus any collection errors."""
    columns = [
        "project_id",
        "short_name",
        "campaign_note",
        "locations",
        "auto_scan",
        "times_per_day",
    ]

    try:
        from fix_ui_zeros import ui_projects_showing_zero  # type: ignore
    except Exception as exc:  # pragma: no cover - import-time error
        return pd.DataFrame(columns=columns), [("import", f"Unable to load fix_ui_zeros: {exc}")]

    project_ids = sorted({str(pid).strip() for pid in ui_projects_showing_zero if str(pid).strip()})
    if not project_ids:
        return pd.DataFrame(columns=columns), []

    try:
        client = GeoEdgeClient()
    except Exception as exc:  # pragma: no cover - configuration issues
        return pd.DataFrame(columns=columns), [("client", f"GeoEdge client unavailable: {exc}")]

    errors: List[Tuple[str, str]] = []
    rows: List[Dict[str, Any]] = []
    for pid in project_ids:
        try:
            raw_project = client.get_project(pid)
        except Exception as exc:
            errors.append((pid, f"GeoEdge API error: {exc}"))
            continue

        if not isinstance(raw_project, dict):
            errors.append((pid, "Unexpected project payload from GeoEdge API"))
            continue

        project = cast(Dict[str, Any], raw_project)

        if not project:
            errors.append((pid, "Project not found via GeoEdge API"))
            continue

        rows.append(
            {
                "project_id": pid,
                "short_name": project.get("name", ""),
                "campaign_note": "",
                "locations": stringify_locations(project.get("locations")),
                "auto_scan": project.get("auto_scan"),
                "times_per_day": project.get("times_per_day"),
            }
        )

    return pd.DataFrame(rows, columns=columns), errors


def _is_zero(value: Any) -> bool:
    try:
        return int(str(value).strip()) == 0
    except (TypeError, ValueError):
        return False


def render_account_summary(filtered_df: pd.DataFrame, db_choice: str) -> None:
    """Render account summary table and update controls."""
    if filtered_df.empty:
        st.info("Account summary unavailable for empty dataset.")
        return

    campaign_values = filtered_df["campaign_id"].dropna().unique().tolist()
    if not campaign_values:
        st.info("No campaign ids in the current selection.")
        return

    account_map = fetch_campaign_accounts(db_choice, campaign_values)
    if not account_map:
        st.info("Accounts could not be resolved for the selected campaigns.")
        return

    status_map = fetch_account_statuses(db_choice, account_map.values())

    frozen_messages = {
        "Frozen - Account is inactive",
        "Frozen - Account is manually paused",
    }

    alerts_client: Optional[GeoEdgeClient] = None
    trigger_lookup: Dict[str, Dict[str, str]] = {}
    alerts_cache: Dict[str, str] = {}
    try:
        if any(status in frozen_messages for status in status_map.values()):
            alerts_client = GeoEdgeClient()
            trigger_lookup = alerts_client.list_alert_trigger_types()
    except Exception as exc:
        st.warning(f"GeoEdge alert metadata unavailable: {exc}")
        alerts_client = None

    account_rows: List[Dict[str, Any]] = []
    inactive_project_ids: Set[str] = set()

    for account_id in sorted(set(account_map.values())):
        related_campaigns = [cid for cid, aid in account_map.items() if aid == account_id]
        campaign_strings = sorted({str(cid) for cid in related_campaigns})
        campaign_mask = filtered_df["campaign_id"].astype(str).isin(campaign_strings)
        account_projects = filtered_df[campaign_mask]

        markets: Set[str] = set()
        for entry in account_projects["locations"]:
            if pd.notna(entry):
                markets.update(loc.strip() for loc in str(entry).split(",") if loc.strip())

        account_status = status_map.get(account_id, "Unknown")
        auto_values = {str(value) for value in account_projects["auto_scan"] if pd.notna(value)}
        time_values = {str(value) for value in account_projects["times_per_day"] if pd.notna(value)}

        alerts_summary = ""
        if account_status in frozen_messages:
            inactive_project_ids.update(
                account_projects["project_id"].dropna().astype(str).tolist()
            )
            if alerts_client is not None:
                disabled_projects = [
                    str(pid)
                    for pid, auto_val, time_val in zip(
                        account_projects["project_id"],
                        account_projects["auto_scan"],
                        account_projects["times_per_day"],
                    )
                    if pd.notna(pid) and _is_zero(auto_val) and _is_zero(time_val)
                ]

                summaries: List[str] = []
                for pid in disabled_projects:
                    cached = alerts_cache.get(pid)
                    if cached is None:
                        cached = summarize_recent_alerts(
                            alerts_client,
                            pid,
                            trigger_lookup=trigger_lookup,
                        )
                        alerts_cache[pid] = cached
                    summaries.append(f"{pid}: {cached}")
                alerts_summary = " | ".join(summaries)

            current_auto = "0"
            current_times = "0"
        else:
            current_auto = ", ".join(sorted(auto_values)) if auto_values else "N/A"
            current_times = ", ".join(sorted(time_values)) if time_values else "N/A"

        account_rows.append(
            {
                "account_id": account_id,
                "account_status": account_status,
                "campaign_count": len(set(related_campaigns)),
                "project_count": int(account_projects["project_id"].nunique()),
                "current_auto_scan": current_auto,
                "current_times_per_day": current_times,
                "campaign_ids": ", ".join(sorted(str(cid) for cid in set(related_campaigns))),
                "markets": ", ".join(sorted(markets)),
                "alerts_summary": alerts_summary,
            }
        )

    accounts_df = pd.DataFrame(account_rows).sort_values("account_id")

    status_options = sorted(accounts_df["account_status"].unique())
    selected_statuses = st.multiselect(
        "Filter by account status",
        status_options,
        default=status_options,
    )
    search_term = st.text_input(
        "Search accounts, campaigns, or markets",
        placeholder="e.g., 46972731 or INACTIVE",
    )

    filtered_accounts = accounts_df.copy()
    if selected_statuses:
        filtered_accounts = filtered_accounts[
            filtered_accounts["account_status"].isin(selected_statuses)
        ]
    if search_term:
        lowered = search_term.lower()
        contains_mask = (
            filtered_accounts["account_id"].astype(str).str.lower().str.contains(lowered)
            | filtered_accounts["account_status"].astype(str).str.lower().str.contains(lowered)
            | filtered_accounts["campaign_ids"].astype(str).str.lower().str.contains(lowered)
            | filtered_accounts["markets"].astype(str).str.lower().str.contains(lowered)
        )
        filtered_accounts = filtered_accounts[contains_mask]

    st.dataframe(
        filtered_accounts,
        width="stretch",
        hide_index=True,
    )

    inactive_projects_sorted = sorted(inactive_project_ids)
    if inactive_projects_sorted:
        if st.button(
            f"Set auto_scan=0 & times=0 for {len(inactive_projects_sorted)} frozen projects",
            key="update_inactive_accounts",
        ):
            with st.spinner("Updating inactive account projects via GeoEdge API..."):
                st.session_state["inactive_update_results"] = apply_zero_schedule(inactive_projects_sorted)

    results = st.session_state.get("inactive_update_results")
    if results:
        st.markdown("##### 🛠️ Update results")
        for pid, message in results:
            st.write(f"{pid}: {message}")

    account_csv = filtered_accounts.to_csv(index=False)
    st.download_button(
        label="⬇️ Download Account Summary",
        data=account_csv,
        file_name=f"geoedge_account_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
    )


def main() -> None:
    st.set_page_config(page_title="GeoEdge Country Projects Dashboard", page_icon="🌍", layout="wide")
    st.title("🌍 GeoEdge Country Projects Dashboard")
    st.caption("Query recent GeoEdge projects, review account status, and inspect Oct 21 remediation work.")

    st.session_state.setdefault("df", None)
    st.session_state.setdefault("total_count", 0)
    st.session_state.setdefault("inactive_update_results", None)
    st.session_state.setdefault("alert_df", None)
    st.session_state.setdefault("alert_meta", None)
    st.session_state.setdefault("alert_fetch_requested", False)
    st.session_state.setdefault(
        "alert_filters",
        {"search": "", "severity": [], "malicious": [], "campaign": "", "countries": []},
    )
    st.session_state.setdefault("alert_range_choice", "Last 90 days")
    st.session_state.setdefault("alert_custom_start", date.today() - timedelta(days=30))
    st.session_state.setdefault("alert_custom_end", date.today())
    st.session_state.setdefault("alert_request_range", None)
    st.session_state.setdefault("alert_force_refetch", False)
    st.session_state.setdefault("alert_last_fetch_token", None)

    DEFAULT_DB = "mysql"
    DEFAULT_DAYS = 90
    DEFAULT_LIMIT = 5000
    ALERT_DAYS = 90
    ALERT_CHUNK = 15
    ALERT_MAX_PAGES: Optional[int] = None  # None = fetch all pages returned by the API

    # Default query scope (filters hidden for now)
    db_choice = DEFAULT_DB
    days = DEFAULT_DAYS
    limit = DEFAULT_LIMIT
    countries_str = ""
    active_specific_date: Optional[str] = None
    project_id_filter: Set[str] = set()
    fetch_api_details = True

    tab_dashboard, tab_alerts, tab_oct21 = st.tabs(
        ["🔎 Project Dashboard", "🚨 Alert Review", "🛠️ Oct 21 Remediation"]
    )

    with tab_dashboard:
        st.markdown(
            f"**Project scope** · DB: `{DEFAULT_DB}` | Window: last {DEFAULT_DAYS} days | Limit: {DEFAULT_LIMIT:,} rows | Countries: all"
        )
        st.caption("Need custom filters for other tabs? Ping me and I'll wire them up tab-by-tab.")

        refresh_pressed = st.button("Refresh project table", width="stretch", key="refresh_project_table")
        run_query = refresh_pressed or st.session_state["df"] is None

        if run_query:
            regex_value: Optional[str] = None
            countries_clean = countries_str.strip()
            if countries_clean:
                try:
                    regex_value = build_regex(countries_clean)
                except Exception as exc:
                    st.error(f"Invalid country input: {exc}")
                    return

            active_project_ids = project_id_filter or None

            with st.spinner("Getting total count..."):
                total_count = get_total_count(
                    db_choice,
                    days,
                    regex_value,
                    specific_date=active_specific_date,
                    project_ids=active_project_ids,
                )
            st.session_state["total_count"] = total_count

            if total_count == 0:
                st.info("No projects found matching the criteria.")
                st.session_state["df"] = None
            else:
                if total_count > limit:
                    st.warning(
                        f"⚠️ Found {total_count:,} total projects, but showing only {limit:,}. Increase the limit to see more."
                    )
                else:
                    st.success(f"Found {total_count:,} matching projects.")

                with st.spinner("Querying database..."):
                    rows = (
                        query_mysql(
                            days,
                            regex_value,
                            limit,
                            specific_date=active_specific_date,
                            project_ids=active_project_ids,
                        )
                        if db_choice == "mysql"
                        else query_vertica(
                            days,
                            regex_value,
                            limit,
                            specific_date=active_specific_date,
                            project_ids=active_project_ids,
                        )
                    )

                if not rows:
                    st.info("The query executed successfully but returned no rows.")
                    st.session_state["df"] = None
                else:
                    df = pd.DataFrame(
                        rows,
                        columns=[
                            "project_id",
                            "campaign_id",
                            "locations",
                            "creation_date",
                            "instruction_status",
                        ],
                    )
                    df.insert(0, "SNo", range(1, len(df) + 1))

                    if fetch_api_details:
                        with st.spinner("Fetching project details from GeoEdge API..."):
                            project_details = fetch_project_details(df["project_id"].astype(str).tolist())
                        df["auto_scan"] = df["project_id"].map(
                            lambda pid: project_details.get(pid, {}).get("auto_scan", "N/A")
                        )
                        df["times_per_day"] = df["project_id"].map(
                            lambda pid: project_details.get(pid, {}).get("times_per_day", "N/A")
                        )
                    else:
                        df["auto_scan"] = "Not fetched"
                        df["times_per_day"] = "Not fetched"

                    st.session_state["df"] = df

        df = st.session_state.get("df")
        total_available = st.session_state.get("total_count", 0)

        if df is None:
            st.info("Run a query to see project results.")
        elif df.empty:
            st.info("The query ran successfully but returned no rows.")
        else:
            st.markdown("### 📊 Results")
            if active_specific_date:
                st.caption(f"Creation date filter: {active_specific_date}")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Available", f"{total_available:,}")
            with col2:
                st.metric("Showing", f"{len(df):,}")
            with col3:
                st.metric("Active Projects", int((df["instruction_status"] == "ACTIVE").sum()))
            with col4:
                st.metric("Unique Campaigns", df["campaign_id"].nunique())

            st.markdown("#### 🔍 Filter Results")
            with st.container(border=True):
                col1, col2, col3 = st.columns(3)

                with col1:
                    all_locations: Set[str] = set()
                    for value in df["locations"]:
                        if pd.notna(value):
                            all_locations.update(loc.strip() for loc in str(value).split(",") if loc.strip())
                    location_filter = st.multiselect(
                        "Filter by location",
                        sorted(all_locations),
                        help="Filter projects by specific markets",
                    )

                with col2:
                    status_filter = st.multiselect(
                        "Filter by status",
                        list(df["instruction_status"].unique()),
                        default=list(df["instruction_status"].unique()),
                    )

                with col3:
                    campaign_filter = st.text_input(
                        "Filter by campaign id",
                        placeholder="e.g., 46972731",
                    )

            filtered_df = df.copy()
            if location_filter:
                filtered_df = filtered_df[
                    filtered_df["locations"].apply(
                        lambda value: any(loc in str(value) for loc in location_filter) if pd.notna(value) else False
                    )
                ]

            if status_filter:
                filtered_df = filtered_df[filtered_df["instruction_status"].isin(status_filter)]

            if campaign_filter:
                filtered_df = filtered_df[
                    filtered_df["campaign_id"].astype(str).str.contains(campaign_filter, na=False)
                ]

            if project_id_filter:
                filtered_df = filtered_df[filtered_df["project_id"].isin(project_id_filter)]

            st.markdown(f"#### 📋 Data Table ({len(filtered_df)} rows)")
            column_config = {
                "project_id": st.column_config.TextColumn("Project ID", width="medium"),
                "campaign_id": st.column_config.NumberColumn("Campaign ID", width="small"),
                "locations": st.column_config.TextColumn("Locations", width="small"),
                "creation_date": st.column_config.DatetimeColumn("Created", width="medium"),
                "instruction_status": st.column_config.TextColumn("Status", width="small"),
                "auto_scan": st.column_config.TextColumn("Auto Scan", width="small"),
                "times_per_day": st.column_config.TextColumn("Times/Day", width="small"),
            }

            st.dataframe(
                filtered_df,
                width="stretch",
                column_config=column_config,
                hide_index=True,
            )

            st.markdown("#### 🧾 Account Summary")
            render_account_summary(filtered_df, db_choice)

            st.markdown("#### 💾 Download Data")
            with st.container(border=True):
                col1, col2, col3 = st.columns(3)

                csv_data = filtered_df.to_csv(index=False)
                json_data = filtered_df.to_json(orient="records", date_format="iso")

                with col1:
                    st.download_button(
                        label="📄 Download CSV",
                        data=csv_data,
                        file_name=f"geoedge_projects_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                    )
                with col2:
                    st.download_button(
                        label="📋 Download JSON",
                        data=json_data,
                        file_name=f"geoedge_projects_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json",
                    )
                with col3:
                    st.info("Excel export is available via the CLI script.")

    with tab_alerts:
        st.subheader("🚨 Alert Review")
        st.caption("Fetch on-demand alert windows (same payload as fetch_all_alerts.py) with caching and quick filters.")

        with st.container(border=True):
            st.markdown("#### 🎯 Alert Data Controls")
            control_cols = st.columns([3, 2])
            preset_options = ["Last 7 days", "Last 30 days", "Last 60 days", "Last 90 days", "Custom range"]

            with control_cols[0]:
                default_idx = (
                    preset_options.index(st.session_state["alert_range_choice"])
                    if st.session_state["alert_range_choice"] in preset_options
                    else len(preset_options) - 1
                )
                range_choice = st.radio(
                    "Preset range",
                    options=preset_options,
                    index=default_idx,
                    horizontal=True,
                )
                st.session_state["alert_range_choice"] = range_choice

                if range_choice == "Custom range":
                    custom_cols = st.columns(2)
                    with custom_cols[0]:
                        st.session_state["alert_custom_start"] = st.date_input(
                            "Start date",
                            value=st.session_state.get("alert_custom_start"),
                            max_value=date.today(),
                        )
                    with custom_cols[1]:
                        st.session_state["alert_custom_end"] = st.date_input(
                            "End date",
                            value=st.session_state.get("alert_custom_end"),
                            max_value=date.today(),
                        )
                else:
                    st.caption("Need a specific window? Switch to Custom range.")
                current_range = resolve_alert_range(
                    st.session_state["alert_range_choice"],
                    st.session_state.get("alert_custom_start"),
                    st.session_state.get("alert_custom_end"),
                )
                current_range_token = f"{current_range['start'].isoformat()}::{current_range['end'].isoformat()}"
                if st.session_state["alert_range_choice"] == "Custom range":
                    preview_start = st.session_state.get("alert_custom_start") or current_range["start"].date()
                    preview_end = st.session_state.get("alert_custom_end") or preview_start
                else:
                    preview_start = current_range["start"].date()
                    preview_end = current_range["end"].date()
                st.caption(
                    f"Selected window: {preview_start:%d %b %Y} → {preview_end:%d %b %Y} ({current_range['days']} day span)"
                )

            with control_cols[1]:
                st.markdown("##### Actions")
                fetch_latest = st.button("Run alert query", width="stretch")
                fetch_missing = st.button("Fetch remaining days scan", width="stretch")
                clear_cache_btn = st.button(
                    "Clear alert cache",
                    width="stretch",
                    type="secondary",
                )
                st.caption("Run alert query = full API scan · Fetch remaining days = cache gap backfill")

            if fetch_latest:
                st.session_state["alert_force_refetch"] = True
            if fetch_missing:
                st.session_state["alert_force_refetch"] = False

            if fetch_latest or fetch_missing:
                st.session_state["alert_request_range"] = {
                    "label": current_range["label"],
                    "start": current_range["start"].isoformat(),
                    "end": current_range["end"].isoformat(),
                    "days": current_range["days"],
                }
                st.session_state["alert_df"] = None
                st.session_state["alert_fetch_requested"] = True

            auto_sync_enabled = True
            if (
                auto_sync_enabled
                and st.session_state.get("alert_last_fetch_token") != current_range_token
                and not st.session_state.get("alert_fetch_requested", False)
                and not (fetch_latest or fetch_missing)
            ):
                st.session_state["alert_request_range"] = {
                    "label": current_range["label"],
                    "start": current_range["start"].isoformat(),
                    "end": current_range["end"].isoformat(),
                    "days": current_range["days"],
                }
                st.session_state["alert_df"] = None
                st.session_state["alert_force_refetch"] = False
                st.session_state["alert_fetch_requested"] = True

            if clear_cache_btn:
                clear_alert_cache()
                st.session_state["alert_df"] = None
                st.session_state["alert_meta"] = None
                st.session_state["alert_request_range"] = None
                st.info("Alert cache cleared. Select a range and run the query again.")

        alert_df = st.session_state.get("alert_df")
        fetch_requested = st.session_state.get("alert_fetch_requested", False)

        if alert_df is None and fetch_requested:
            request_range = st.session_state.get("alert_request_range")
            if request_range:
                start_dt = parse_iso_datetime(request_range.get("start"))
                end_dt = parse_iso_datetime(request_range.get("end"))
                days_requested = int(request_range.get("days", ALERT_DAYS))
                range_label = request_range.get("label") or f"last {days_requested} days"
            else:
                fallback_range = resolve_alert_range(
                    st.session_state["alert_range_choice"],
                    st.session_state.get("alert_custom_start"),
                    st.session_state.get("alert_custom_end"),
                )
                start_dt = fallback_range["start"]
                end_dt = fallback_range["end"]
                days_requested = fallback_range["days"]
                range_label = fallback_range["label"]

            force_full_scan = st.session_state.get("alert_force_refetch", False)
            mode_label = "full scan" if force_full_scan else "gap scan"
            try:
                with st.spinner(f"Fetching alerts for {range_label} ({mode_label})..."):
                    alert_df, meta = fetch_alert_history(
                        days_requested,
                        ALERT_CHUNK,
                        ALERT_MAX_PAGES,
                        start_datetime=start_dt,
                        end_datetime=end_dt,
                        force_full_scan=force_full_scan,
                    )
                st.session_state["alert_df"] = alert_df
                st.session_state["alert_meta"] = {
                    **meta,
                    "days": days_requested,
                    "chunk_days": ALERT_CHUNK,
                    "max_pages": ALERT_MAX_PAGES if ALERT_MAX_PAGES is not None else "all",
                    "requested_label": range_label,
                }
                if start_dt and end_dt:
                    st.session_state["alert_last_fetch_token"] = f"{start_dt.isoformat()}::{end_dt.isoformat()}"
            except Exception as exc:
                st.error(f"Alert fetch failed: {exc}")
            finally:
                st.session_state["alert_fetch_requested"] = False
                st.session_state["alert_force_refetch"] = False

            alert_df = st.session_state.get("alert_df")

        alert_meta = st.session_state.get("alert_meta") or {}
        requested_label = alert_meta.get("requested_label") or f"last {alert_meta.get('days', ALERT_DAYS)} days"
        active_view = resolve_alert_range(
            st.session_state["alert_range_choice"],
            st.session_state.get("alert_custom_start"),
            st.session_state.get("alert_custom_end"),
        )

        if alert_df is None:
            if fetch_requested:
                st.info("Fetching alerts... hold tight.")
            else:
                st.warning("Click Run alert query to load data.")
        elif alert_df.empty:
            st.info(f"GeoEdge returned zero alerts for {requested_label}.")
        else:
            window_start = alert_meta.get("window_start")
            window_end = alert_meta.get("window_end")
            window_start_dt = parse_iso_datetime(window_start)
            window_end_dt = parse_iso_datetime(window_end)
            view_start_dt = active_view["start"]
            view_end_dt = active_view["end"]
            view_label = active_view["label"]
            coverage_days: Optional[int] = None
            if window_start_dt and window_end_dt and window_end_dt >= window_start_dt:
                coverage_days = max(0, int((window_end_dt - window_start_dt).days))

            normalized_alerts = alert_df.copy()
            normalized_alerts["event_datetime"] = pd.to_datetime(
                normalized_alerts["event_datetime"], errors="coerce", utc=True
            )
            normalized_alerts = normalized_alerts.dropna(subset=["event_datetime"])
            normalized_alerts.sort_values("event_datetime", ascending=False, inplace=True)
            normalized_alerts.drop_duplicates(subset=["alert_id"], keep="first", inplace=True)
            if view_start_dt and view_end_dt:
                date_mask = (
                    (normalized_alerts["event_datetime"] >= view_start_dt)
                    & (normalized_alerts["event_datetime"] <= view_end_dt)
                )
                cleaned_df = normalized_alerts[date_mask].copy()
            else:
                cleaned_df = normalized_alerts.copy()

            view_missing_days = 0
            view_end_gap_days = 0
            if window_start_dt and view_start_dt and window_start_dt > view_start_dt:
                view_missing_days = max(0, int((window_start_dt - view_start_dt).days))
            if window_end_dt and view_end_dt and window_end_dt < view_end_dt:
                view_end_gap_days = max(0, int((view_end_dt - window_end_dt).days))

            st.markdown("### 📈 Alert Snapshot")
            cols = st.columns(4)
            with cols[0]:
                st.metric("Alerts", f"{len(cleaned_df):,}")
            with cols[1]:
                st.metric("Projects", cleaned_df["project_id"].nunique())
            with cols[2]:
                st.metric("Campaigns", cleaned_df["campaign_id_guess"].nunique())
            with cols[3]:
                st.metric("Target Countries", cleaned_df["location_name"].nunique())

            detail_cols = st.columns(2)
            with detail_cols[0]:
                st.metric("Unique Alert Names", cleaned_df["alert_name"].nunique())
            with detail_cols[1]:
                chunk_info = f"{alert_meta.get('chunks', '?')} chunks"
                st.metric("Window", chunk_info, help=f"{window_start} → {window_end}")

            if coverage_days is not None:
                st.caption(
                    f"Cache coverage: {coverage_days} days ({window_start or 'n/a'} → {window_end or 'n/a'})"
                )
            st.caption(
                "Latest refresh mode: "
                + ("Full API scan" if alert_meta.get("full_scan") else "Cache gap backfill")
            )
            st.caption(f"Last fetch window: {requested_label}")
            st.caption(f"Active filter: {view_label}")
            if view_missing_days > 0:
                st.warning(
                    f"{view_missing_days} day(s) missing at the start of the selected window. Click 'Fetch remaining days scan' to backfill.",
                    icon="⚠️",
                )
            if view_end_gap_days > 0:
                st.warning(
                    f"Selected window extends {view_end_gap_days} day(s) past cached data. Re-run the query to refresh the latest alerts.",
                    icon="🕒",
                )

            chunk_stats = alert_meta.get("chunk_stats") or []
            if chunk_stats:
                stats_df = pd.DataFrame(chunk_stats)
                stats_df["start"] = pd.to_datetime(stats_df["start"], errors="coerce")
                stats_df["end"] = pd.to_datetime(stats_df["end"], errors="coerce")
                stats_df.sort_values("start", inplace=True)
                missing_chunk_df = stats_df[stats_df["alerts"] == 0]
                if not missing_chunk_df.empty:
                    st.warning(
                        f"{len(missing_chunk_df)} chunk(s) returned zero alerts. Run 'Fetch remaining days scan' to backfill.",
                        icon="📉",
                    )
                with st.expander("Chunk coverage details", expanded=False):
                    st.dataframe(
                        stats_df.rename(
                            columns={
                                "chunk_id": "Chunk",
                                "start": "Start",
                                "end": "End",
                                "alerts": "Alerts",
                            }
                        ),
                        width="stretch",
                        hide_index=True,
                    )
                    chunk_report = {
                        "requested_start": view_start_dt.isoformat() if view_start_dt else None,
                        "requested_end": view_end_dt.isoformat() if view_end_dt else None,
                        "chunk_days": ALERT_CHUNK,
                        "total_chunks": len(chunk_stats),
                        "total_alerts": int(stats_df["alerts"].sum()),
                        "missing_chunks": missing_chunk_df.to_dict(orient="records"),
                        "chunk_stats": chunk_stats,
                    }
                    st.download_button(
                        "Download chunk report JSON",
                        data=json.dumps(chunk_report, indent=2),
                        file_name=f"chunk_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json",
                    )

                    st.markdown("##### 🔄 Backend Chunk Scan")
                    backend_state = st.session_state.setdefault("backend_chunk_scan", {})

                    if "backend_chunk_days" not in backend_state:
                        backend_state["backend_chunk_days"] = 7
                    if "backend_page_limit" not in backend_state:
                        backend_state["backend_page_limit"] = 5000
                    if "backend_max_pages" not in backend_state:
                        backend_state["backend_max_pages"] = 0

                    control_cols = st.columns([1, 1, 1, 1])
                    backend_chunk_days = control_cols[0].number_input(
                        "Chunk days",
                        min_value=1,
                        max_value=30,
                        value=int(backend_state.get("backend_chunk_days", 7)),
                        step=1,
                        help="How many days each backend chunk should cover.",
                    )
                    backend_page_limit = control_cols[1].number_input(
                        "Page limit",
                        min_value=100,
                        max_value=10000,
                        value=int(backend_state.get("backend_page_limit", 5000)),
                        step=100,
                        help="Per-chunk limit passed to the GeoEdge API.",
                    )
                    backend_max_pages = control_cols[2].number_input(
                        "Max pages (0 = ∞)",
                        min_value=0,
                        max_value=200,
                        value=int(backend_state.get("backend_max_pages", 0)),
                        step=1,
                        help="Optional safety cap on pagination per chunk.",
                    )
                    run_backend_scan = control_cols[3].button(
                        "Run backend chunk scan",
                        use_container_width=True,
                    )

                    if run_backend_scan:
                        if not (view_start_dt and view_end_dt):
                            st.warning("Select a date window before running the backend chunk scan.")
                        else:
                            try:
                                with st.spinner("Collecting chunk stats directly from GeoEdge..."):
                                    backend_report = build_backend_chunk_report(
                                        view_start_dt,
                                        view_end_dt,
                                        chunk_days=int(backend_chunk_days),
                                        page_limit=int(backend_page_limit),
                                        max_pages=int(backend_max_pages),
                                    )
                                backend_state.update(
                                    {
                                        "backend_chunk_days": int(backend_chunk_days),
                                        "backend_page_limit": int(backend_page_limit),
                                        "backend_max_pages": int(backend_max_pages),
                                        "report": backend_report,
                                        "updated_at": datetime.now(timezone.utc).isoformat(),
                                    }
                                )
                                st.session_state["backend_chunk_scan"] = backend_state
                                st.success(
                                    f"Backend scan complete: {backend_report['total_chunks']} chunks / {backend_report['total_alerts']:,} alerts."
                                )
                            except Exception as exc:
                                st.error(f"Backend chunk scan failed: {exc}")

                    stored_report = st.session_state.get("backend_chunk_scan", {}).get("report")
                    if stored_report:
                        last_run = st.session_state.get("backend_chunk_scan", {}).get("updated_at")
                        st.caption(
                            f"Last backend scan: {last_run or '—'} • {stored_report['total_chunks']} chunks • {stored_report['total_alerts']:,} alerts"
                        )
                        backend_df = pd.DataFrame(stored_report.get("chunk_stats", []))
                        if not backend_df.empty:
                            backend_df["start"] = pd.to_datetime(backend_df["start"], errors="coerce")
                            backend_df["end"] = pd.to_datetime(backend_df["end"], errors="coerce")
                            backend_df.sort_values("start", inplace=True)
                            st.dataframe(
                                backend_df.rename(
                                    columns={
                                        "chunk_id": "Chunk",
                                        "start": "Start",
                                        "end": "End",
                                        "alerts": "Alerts",
                                    }
                                ),
                                width="stretch",
                                hide_index=True,
                            )
                        st.download_button(
                            "Download backend chunk report JSON",
                            data=json.dumps(stored_report, indent=2),
                            file_name=f"backend_chunk_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            mime="application/json",
                            key="backend_chunk_report_download_btn",
                        )

            if cleaned_df.empty:
                st.warning(
                    "No alerts fall within the selected date window. Expand the selection or rerun the alert query to pull fresh data.",
                    icon="🗓️",
                )
            else:
                cleaned_df["trigger_metadata_str"] = cleaned_df["trigger_metadata"].apply(
                    lambda value: json.dumps(value, ensure_ascii=False) if isinstance(value, dict) else str(value or "")
                )
                cleaned_df["severity"] = cleaned_df["severity"].fillna("Unknown")
                cleaned_df["malicious_type"] = cleaned_df["malicious_type"].fillna("Unlabeled")
                cleaned_df["security_url_count"] = cleaned_df["security_url_count"].fillna(0)

                severity_options = sorted(cleaned_df["severity"].dropna().unique().tolist())
                malicious_options = sorted(cleaned_df["malicious_type"].dropna().unique().tolist())
                country_options = sorted(
                    cleaned_df["location_name"].dropna().astype(str).str.strip().replace({"": pd.NA}).dropna().unique().tolist()
                )

                # Initialize widget state once so users can type before running filters
                active_filter_state = st.session_state.setdefault(
                    "alert_filters",
                    {"search": "", "severity": [], "malicious": [], "campaign": "", "countries": []},
                )
                if "alert_search_input" not in st.session_state:
                    st.session_state["alert_search_input"] = active_filter_state.get("search", "")
                if "alert_severity_input" not in st.session_state:
                    st.session_state["alert_severity_input"] = active_filter_state.get("severity") or severity_options
                if "alert_malicious_input" not in st.session_state:
                    st.session_state["alert_malicious_input"] = active_filter_state.get("malicious") or malicious_options
                if "alert_campaign_input" not in st.session_state:
                    st.session_state["alert_campaign_input"] = active_filter_state.get("campaign", "")
                if "alert_country_input" not in st.session_state:
                    st.session_state["alert_country_input"] = active_filter_state.get("countries") or country_options

                st.markdown("#### 🎛️ Filter Alerts")
                filter_cols = st.columns([2, 1, 1])
                filter_cols[0].text_input(
                    "Search project, ID, or alert text",
                    placeholder="project name, ID, alert name, or metadata",
                    key="alert_search_input",
                )
                filter_cols[1].multiselect(
                    "Severity",
                    options=severity_options,
                    key="alert_severity_input",
                    help="Limit to one or more severities.",
                )
                filter_cols[2].multiselect(
                    "Malicious type",
                    options=malicious_options,
                    key="alert_malicious_input",
                    help="Match specific GeoEdge classifications.",
                )

                extra_cols = st.columns([1, 1])
                extra_cols[0].text_input(
                    "Campaign ID contains",
                    placeholder="46972731",
                    key="alert_campaign_input",
                )
                extra_cols[1].multiselect(
                    "Target countries",
                    options=country_options,
                    key="alert_country_input",
                    help="Filter by GeoEdge location/market",
                )

                if st.button("Apply alert filters", width="stretch", key="apply_alert_filters_btn"):
                    st.session_state["alert_filters"] = {
                        "search": st.session_state.get("alert_search_input", ""),
                        "severity": list(st.session_state.get("alert_severity_input", [])),
                        "malicious": list(st.session_state.get("alert_malicious_input", [])),
                        "campaign": st.session_state.get("alert_campaign_input", ""),
                        "countries": list(st.session_state.get("alert_country_input", [])),
                    }

                applied_filters = st.session_state.get("alert_filters", {})
                filtered_alerts = cleaned_df.copy()

                alert_search = applied_filters.get("search", "").strip().lower()
                if alert_search:
                    search_mask = (
                        filtered_alerts["project_name"].astype(str).str.lower().str.contains(alert_search, na=False)
                        | filtered_alerts["project_id"].astype(str).str.lower().str.contains(alert_search, na=False)
                        | filtered_alerts["alert_name"].astype(str).str.lower().str.contains(alert_search, na=False)
                        | filtered_alerts["trigger_metadata_str"].astype(str).str.lower().str.contains(alert_search, na=False)
                    )
                    filtered_alerts = filtered_alerts[search_mask]

                active_severity = [value for value in applied_filters.get("severity", []) if value in severity_options]
                if len(active_severity) != len(applied_filters.get("severity", [])):
                    st.session_state["alert_filters"]["severity"] = active_severity
                if active_severity and len(active_severity) < len(severity_options):
                    filtered_alerts = filtered_alerts[filtered_alerts["severity"].isin(active_severity)]

                active_malicious = [value for value in applied_filters.get("malicious", []) if value in malicious_options]
                if len(active_malicious) != len(applied_filters.get("malicious", [])):
                    st.session_state["alert_filters"]["malicious"] = active_malicious
                if active_malicious and len(active_malicious) < len(malicious_options):
                    filtered_alerts = filtered_alerts[filtered_alerts["malicious_type"].isin(active_malicious)]

                campaign_query = applied_filters.get("campaign", "").strip()
                if campaign_query:
                    filtered_alerts = filtered_alerts[
                        filtered_alerts["campaign_id_guess"].astype(str).str.contains(campaign_query, case=False, na=False)
                    ]

                active_countries = [value for value in applied_filters.get("countries", []) if value in country_options]
                if len(active_countries) != len(applied_filters.get("countries", [])):
                    st.session_state["alert_filters"]["countries"] = active_countries
                if country_options and active_countries and len(active_countries) < len(country_options):
                    filtered_alerts = filtered_alerts[filtered_alerts["location_name"].isin(active_countries)]

                st.caption(f"Showing {len(filtered_alerts):,} of {len(cleaned_df):,} alerts after filters.")

                if filtered_alerts.empty:
                    st.info("No alerts match the current filters. Adjust the selections above and try again.")
                else:
                    display_columns = [
                        "event_datetime",
                        "alert_name",
                        "campaign_id_guess",
                        "project_id",
                        "project_name",
                        "location_name",
                        "severity",
                        "malicious_type",
                        "security_url_count",
                        "trigger_metadata_str",
                        "alert_details_url",
                        "screenshot_url",
                    ]

                    st.markdown("#### 🔍 Latest Alerts")
                    alert_column_config = {
                        "SNo": st.column_config.NumberColumn("#", width="small"),
                        "event_datetime": st.column_config.DatetimeColumn("Event Time", width="medium"),
                        "alert_name": st.column_config.TextColumn("Alert", width="large"),
                        "campaign_id_guess": st.column_config.TextColumn("Campaign ID", width="small"),
                        "project_id": st.column_config.TextColumn("Project ID", width="small"),
                        "project_name": st.column_config.TextColumn("Project Name", width="large"),
                        "location_name": st.column_config.TextColumn("Target Country", width="small"),
                        "severity": st.column_config.TextColumn("Severity", width="small"),
                        "malicious_type": st.column_config.TextColumn("Malicious Type", width="small"),
                        "security_url_count": st.column_config.NumberColumn("Security URLs", width="small"),
                        "trigger_metadata_str": st.column_config.TextColumn("Trigger Metadata", width="large"),
                        "alert_details_url": st.column_config.TextColumn("Alert Details URL", width="small"),
                        "screenshot_url": st.column_config.TextColumn("Screenshot URL", width="small"),
                    }
                    alert_display_df = filtered_alerts[display_columns].copy()
                    alert_display_df.insert(0, "SNo", range(1, len(alert_display_df) + 1))
                    st.dataframe(
                        alert_display_df,
                        width="stretch",
                        hide_index=True,
                        column_config=alert_column_config,
                    )

                    st.markdown("#### 🪟 Summaries")
                    summary_tabs = st.tabs(["By Alert", "By Trigger", "By Project"])

                    with summary_tabs[0]:
                        summary_alert = (
                            filtered_alerts.groupby("alert_name", dropna=False)
                            .size()
                            .reset_index(name="alert_count")
                            .sort_values("alert_count", ascending=False)
                        )
                        st.dataframe(summary_alert, width="stretch", hide_index=True)

                    with summary_tabs[1]:
                        summary_trigger = (
                            filtered_alerts.groupby("trigger_metadata_str", dropna=False)
                            .size()
                            .reset_index(name="alert_count")
                            .sort_values("alert_count", ascending=False)
                        )
                        st.dataframe(summary_trigger, width="stretch", hide_index=True)

                    with summary_tabs[2]:
                        summary_project = (
                            filtered_alerts.groupby(["project_id", "project_name"], dropna=False)
                            .size()
                            .reset_index(name="alert_count")
                            .sort_values("alert_count", ascending=False)
                        )
                        st.dataframe(summary_project, width="stretch", hide_index=True)

                    st.markdown("#### 💾 Download Alerts")
                    download_cols = st.columns(3)
                    csv_export = filtered_alerts.to_csv(index=False)
                    json_export = filtered_alerts.to_json(orient="records", date_format="iso")
                    export_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                    with download_cols[0]:
                        st.download_button(
                            label="📄 CSV",
                            data=csv_export,
                            file_name=f"geoedge_alerts_{export_stamp}.csv",
                            mime="text/csv",
                        )
                    with download_cols[1]:
                        st.download_button(
                            label="📋 JSON",
                            data=json_export,
                            file_name=f"geoedge_alerts_{export_stamp}.json",
                            mime="application/json",
                        )
                    with download_cols[2]:
                        st.info(
                            "Need Excel? Use the CLI script or open the CSV in Excel for full fidelity.",
                            icon="ℹ️",
                        )

    with tab_oct21:
        st.subheader("Projects Restored on 21 Oct 2025")
        st.caption("Live data sourced from fix_ui_zeros.py and the GeoEdge API.")

        with st.spinner("Loading Oct 21 remediation set..."):
            oct21_df, oct21_errors = build_oct21_dataframe()

        if oct21_errors:
            for pid, message in oct21_errors:
                st.warning(f"{pid[:8]}…: {message}")

        if oct21_df.empty:
            st.info("No Oct 21 remediation projects found.")
        else:
            total_projects = len(oct21_df)
            location_tokens: Set[str] = set()
            for entry in oct21_df["locations"]:
                for token in str(entry).split(","):
                    token = token.strip()
                    if token:
                        location_tokens.add(token)
            auto_ok = sum(1 for value in oct21_df["auto_scan"] if str(value) == "1")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Projects", total_projects)
            with col2:
                st.metric("Markets", len(location_tokens))
            with col3:
                st.metric("Auto Scan = 1", f"{auto_ok}/{total_projects}")

            st.markdown("#### 🔍 Filter Oct 21 Results")
            col1, col2 = st.columns([2, 1])

            with col1:
                location_filter = st.multiselect(
                    "Filter by location",
                    sorted(location_tokens),
                    help="Only show projects matching selected markets",
                )

            with col2:
                search_term = st.text_input(
                    "Search note or name",
                    placeholder="Country, campaign, or project name",
                )

            filtered_oct21 = oct21_df.copy()
            if location_filter:
                filtered_oct21 = filtered_oct21[
                    filtered_oct21["locations"].apply(
                        lambda value: any(loc in str(value) for loc in location_filter) if pd.notna(value) else False
                    )
                ]

            if search_term:
                lowered = search_term.lower()
                filtered_oct21 = filtered_oct21[
                    filtered_oct21.apply(
                        lambda row: lowered in str(row["campaign_note"]).lower()
                        or lowered in str(row["short_name"]).lower(),
                        axis=1,
                    )
                ]

            display_oct21 = filtered_oct21.copy()
            display_oct21.insert(0, "SNo", range(1, len(display_oct21) + 1))

            column_config = {
                "project_id": st.column_config.TextColumn("Project ID", width="medium"),
                "short_name": st.column_config.TextColumn("Project", width="large"),
                "campaign_note": st.column_config.TextColumn("Campaign Note", width="large"),
                "locations": st.column_config.TextColumn("Locations", width="small"),
                "auto_scan": st.column_config.TextColumn("Auto Scan", width="small"),
                "times_per_day": st.column_config.TextColumn("Times/Day", width="small"),
            }

            st.dataframe(
                display_oct21[
                    [
                        "SNo",
                        "project_id",
                        "short_name",
                        "campaign_note",
                        "locations",
                        "auto_scan",
                        "times_per_day",
                    ]
                ],
                width="stretch",
                column_config=column_config,
                hide_index=True,
            )

            csv_data = filtered_oct21.to_csv(index=False)
            st.download_button(
                label="📄 Download Oct 21 CSV",
                data=csv_data,
                file_name=f"geoedge_oct21_projects_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
            )


if __name__ == "__main__":
    main()