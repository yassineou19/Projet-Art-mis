"""Backfill historical launches year by year.

The script uses dev.historical_backfill_state as a checkpoint table. It only
loads years that are not complete and resumes from last_offset for each year.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone

import requests

from src.database import connection
from src.ingestion.api_client import auth_headers, wait_for_available_quota
from src.ingestion.raw_loader import insert_raw_launches
from src.ingestion.transform import transform_launches


BASE_URL = "https://ll.thespacedevs.com/2.3.0/launches/"
LIMIT = int(os.getenv("HISTORICAL_BACKFILL_LIMIT", "100"))
MAX_YEARS = int(os.getenv("HISTORICAL_BACKFILL_MAX_YEARS", "2"))
SLEEP_SECONDS = int(os.getenv("HISTORICAL_BACKFILL_SLEEP_SECONDS", "300"))
MAX_API_CALLS = int(os.getenv("HISTORICAL_BACKFILL_MAX_API_CALLS", "12"))
RESERVED_API_CALLS = int(os.getenv("HISTORICAL_RESERVED_API_CALLS", "3"))


def sync_loaded_counts() -> None:
    query = """
    with year_counts as (
        select launch_year as year, count(*)::int as rows_loaded
        from dev.launches_clean
        where launch_year between 1957 and 2025
        group by launch_year
    )
    update dev.historical_backfill_state h
    set rows_loaded = coalesce(c.rows_loaded, 0),
        status = case
            when h.rows_expected is not null and coalesce(c.rows_loaded, 0) >= h.rows_expected
                then 'complete'
            when coalesce(c.rows_loaded, 0) > 0
                then 'loaded_current'
            else 'pending'
        end,
        updated_at = now()
    from year_counts c
    where h.year = c.year;

    update dev.historical_backfill_state
    set rows_loaded = 0,
        status = 'pending',
        last_offset = 0,
        updated_at = now()
    where year not in (
        select launch_year
        from dev.launches_clean
        where launch_year between 1957 and 2025
    );
    """
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
        conn.commit()


def count_loaded_year(year: int) -> int:
    query = """
    select count(*)::int
    from dev.launches_clean
    where launch_year = %s;
    """
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (year,))
            return cur.fetchone()[0]


def years_to_backfill() -> list[dict]:
    query = """
    select year, rows_expected, rows_loaded, last_offset
    from dev.historical_backfill_state
    where status in ('pending', 'loaded_current', 'rate_limited', 'failed')
      and rows_expected is not null
      and rows_loaded < rows_expected
    order by year
    limit %s;
    """
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (MAX_YEARS,))
            rows = cur.fetchall()

    return [
        {
            "year": row[0],
            "rows_expected": row[1],
            "rows_loaded": row[2],
            "last_offset": row[3],
        }
        for row in rows
    ]


def update_state(
    year: int,
    status: str,
    rows_loaded: int,
    last_offset: int,
    error: str | None = None,
) -> None:
    query = """
    update dev.historical_backfill_state
    set status = %s,
        rows_loaded = %s,
        last_offset = %s,
        last_error = %s,
        updated_at = %s
    where year = %s;
    """
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (
                    status,
                    rows_loaded,
                    last_offset,
                    error,
                    datetime.now(timezone.utc),
                    year,
                ),
            )
        conn.commit()


def fetch_year_page(year: int, offset: int) -> tuple[int, list[dict]]:
    wait_for_available_quota(RESERVED_API_CALLS)
    response = requests.get(
        BASE_URL,
        params={
            "limit": LIMIT,
            "offset": offset,
            "net__gte": f"{year}-01-01T00:00:00Z",
            "net__lt": f"{year + 1}-01-01T00:00:00Z",
        },
        headers=auth_headers(),
        timeout=45,
    )
    response.raise_for_status()
    payload = response.json()
    return int(payload.get("count", 0)), payload.get("results", [])


def backfill_year(year_state: dict, calls_remaining: int) -> tuple[bool, int]:
    year = year_state["year"]
    rows_expected = int(year_state["rows_expected"])
    rows_loaded = int(year_state["rows_loaded"])
    offset = int(year_state["last_offset"] or 0)
    if offset >= rows_expected and rows_loaded < rows_expected:
        offset = 0

    update_state(year, "running", rows_loaded, offset)
    print(f"Backfilling {year}: loaded={rows_loaded}, expected={rows_expected}, offset={offset}")

    while rows_loaded < rows_expected:
        if calls_remaining <= 0:
            update_state(year, "pending", rows_loaded, offset)
            print("Hourly API call budget reached. Stopping cleanly.")
            return False, calls_remaining

        try:
            api_count, results = fetch_year_page(year, offset)
            calls_remaining -= 1
        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            if status_code == 429:
                update_state(year, "rate_limited", rows_loaded, offset, str(exc))
                print(f"Rate limited on {year}. Stopping.")
                return False, calls_remaining
            update_state(year, "failed", rows_loaded, offset, str(exc))
            raise

        if api_count != rows_expected:
            rows_expected = api_count

        if not results:
            status = "complete" if rows_loaded >= rows_expected else "failed"
            error = None if status == "complete" else "API returned no rows before year was complete."
            update_state(year, status, rows_loaded, offset, error)
            return status == "complete", calls_remaining

        stats = insert_raw_launches(results)
        transform_launches()

        offset += len(results)
        rows_loaded = count_loaded_year(year)
        status = "complete" if rows_loaded >= rows_expected else "pending"
        update_state(year, status, rows_loaded, offset)
        print(f"{year}: +{stats['inserted']} inserted, +{stats['updated']} updated, {rows_loaded}/{rows_expected}")

        if rows_loaded < rows_expected and offset >= rows_expected:
            update_state(
                year,
                "failed",
                rows_loaded,
                0,
                "Scanned the full API year but the clean table is still incomplete.",
            )
            return False, calls_remaining

        if rows_loaded < rows_expected:
            time.sleep(SLEEP_SECONDS)

    update_state(year, "complete", rows_loaded, offset)
    return True, calls_remaining


def main() -> None:
    sync_loaded_counts()
    targets = years_to_backfill()
    if not targets:
        print("No audited incomplete years to backfill.")
        return

    calls_remaining = MAX_API_CALLS
    for index, year_state in enumerate(targets, start=1):
        ok, calls_remaining = backfill_year(year_state, calls_remaining)
        if not ok:
            break
        if index < len(targets):
            time.sleep(SLEEP_SECONDS)


if __name__ == "__main__":
    main()
