#!/usr/bin/env python3
"""Build an account list from the "Final Updated Config List" sheet.

Reads the workbook exported from the country dashboard, maps each campaign to its
syndicator/account via MySQL, removes the accounts already covered in the "Update
on 3 Nov" sheet, and writes the remaining unique account IDs to a text file.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set

import pandas as pd
import pymysql
from dotenv import load_dotenv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract account IDs from dashboard workbook")
    parser.add_argument(
        "--workbook",
        default="projects _ Italy_France_Germany_Spain_ in last 7 days .xlsx",
        help="Path to the Excel workbook",
    )
    parser.add_argument(
        "--final-sheet",
        default="Final Updated Config List",
        help="Sheet containing the 1/72 project list",
    )
    parser.add_argument(
        "--exclude-sheet",
        default="Update on 3 Nov",
        help="Sheet containing accounts already reverted to 0/0",
    )
    parser.add_argument(
        "--output",
        default="accounts_from_final_list.txt",
        help="File that will receive the unique account IDs (one per line)",
    )
    return parser.parse_args()


def load_campaigns(path: Path, sheet: str) -> List[int]:
    df = pd.read_excel(path, sheet_name=sheet)
    if "campaign_id" not in df.columns:
        raise RuntimeError(f"Sheet '{sheet}' does not have a campaign_id column")
    ids = [int(cid) for cid in df["campaign_id"].dropna().astype(int).tolist()]
    return ids


def load_excluded_accounts(path: Path, sheet: str) -> Set[str]:
    try:
        df = pd.read_excel(path, sheet_name=sheet)
    except ValueError:
        return set()
    if "account_id" not in df.columns:
        return set()
    return {
        str(int(value))
        for value in df["account_id"].dropna().tolist()
        if str(value).strip()
    }


def fetch_campaign_accounts(campaign_ids: Sequence[int]) -> Dict[int, str]:
    if not campaign_ids:
        return {}

    load_dotenv()
    host = os.getenv("MYSQL_HOST")
    port = int(os.getenv("MYSQL_PORT", "3306"))
    user = os.getenv("MYSQL_USER")
    password = os.getenv("MYSQL_PASSWORD")
    database = os.getenv("MYSQL_DB")

    if not all([host, user, password, database]):
        raise RuntimeError("Missing MySQL credentials in environment/.env")

    placeholders = ", ".join(["%s"] * len(campaign_ids))
    sql = f"SELECT id, syndicator_id FROM trc.sp_campaigns WHERE id IN ({placeholders})"

    connection = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        cursorclass=pymysql.cursors.Cursor,
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, tuple(campaign_ids))
            return {int(row[0]): str(int(row[1])) for row in cursor.fetchall() if row[1] is not None}
    finally:
        connection.close()


def main() -> int:
    args = parse_args()
    workbook_path = Path(args.workbook).expanduser().resolve()
    campaigns = load_campaigns(workbook_path, args.final_sheet)
    mapping = fetch_campaign_accounts(campaigns)
    excluded = load_excluded_accounts(workbook_path, args.exclude_sheet)

    accounts: Set[str] = set()
    missing_campaigns: List[int] = []
    for cid in campaigns:
        account = mapping.get(cid)
        if account is None:
            missing_campaigns.append(cid)
            continue
        accounts.add(account)

    accounts -= excluded

    output_path = Path(args.output).resolve()
    output_path.write_text("\n".join(sorted(accounts)), encoding="utf-8")

    print(f"Workbook: {workbook_path}")
    print(f"Campaigns in sheet: {len(campaigns)}")
    print(f"Mapped campaigns: {len(mapping)}")
    print(f"Excluded accounts: {len(excluded)}")
    print(f"Unique accounts written: {len(accounts)} -> {output_path}")
    if missing_campaigns:
        print(f"Campaigns missing account mapping: {len(missing_campaigns)} (see log)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
