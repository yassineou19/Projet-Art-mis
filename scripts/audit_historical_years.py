"""Audit historical launch coverage by year.

This script fills dev.historical_backfill_state.rows_expected from The Space
Devs API and marks years as complete only when rows_loaded >= rows_expected.
It stops cleanly on API rate limit.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone

import requests

from src.database import connection
from src.ingestion.api_client import auth_headers, wait_for_available_quota


BASE_URL = "https://ll.thespacedevs.com/2.3.0/launches/"
START_YEAR = int(os.getenv("HISTORICAL_START_YEAR", "1957"))
END_YEAR = int(os.getenv("HISTORICAL_END_YEAR", "2025"))
MAX_YEARS = int(os.getenv("HISTORICAL_AUDIT_MAX_YEARS", "10"))
SLEEP_SECONDS = int(os.getenv("HISTORICAL_AUDIT_SLEEP_SECONDS", "20"))
RESERVED_API_CALLS = int(os.getenv("HISTORICAL_RESERVED_API_CALLS", "3"))


def ensure_state_table() -> None:
    query = """
    create table if not exists dev.historical_backfill_state (
        year int primary key check (year between 1957 and 2025),
        status text not null default 'pending' check (
            status in (
                'pending',
                'loaded_current',
                'running',
                'complete',
                'rate_limited',
                'failed'
            )
        ),
        rows_expected int,
        rows_loaded int not null default 0,
        last_offset int not null default 0,
        last_error text,
        updated_at timestamptz not null default now()
    );
    """
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
        conn.commit()


def sync_loaded_counts() -> None:
    query = """
    with year_counts as (
        select launch_year as year, count(*)::int as rows_loaded
        from dev.launches_clean
        where launch_year between %s and %s
        group by launch_year
    ), all_years as (
        select generate_series(%s, %s) as year
    )
    insert into dev.historical_backfill_state (
        year,
        status,
        rows_loaded,
        updated_at
    )
    select
        y.year,
        case when coalesce(c.rows_loaded, 0) > 0 then 'loaded_current' else 'pending' end,
        coalesce(c.rows_loaded, 0),
        now()
    from all_years y
    left join year_counts c using (year)
    on conflict (year) do update set
        rows_loaded = excluded.rows_loaded,
        status = case
            when dev.historical_backfill_state.status = 'complete'
                 and excluded.rows_loaded >= coalesce(dev.historical_backfill_state.rows_expected, 0)
                then 'complete'
            when excluded.rows_loaded > 0
                then 'loaded_current'
            else 'pending'
        end,
        updated_at = now();
    """
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (START_YEAR, END_YEAR, START_YEAR, END_YEAR))
        conn.commit()


def years_to_audit() -> list[tuple[int, int]]:
    query = """
    select year, rows_loaded
    from dev.historical_backfill_state
    where year between %s and %s
      and (
          rows_expected is null
          or status in ('pending', 'loaded_current', 'rate_limited', 'failed')
      )
    order by year
    limit %s;
    """
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (START_YEAR, END_YEAR, MAX_YEARS))
            return cur.fetchall()


def fetch_expected_count(year: int) -> int:
    wait_for_available_quota(RESERVED_API_CALLS)
    response = requests.get(
        BASE_URL,
        params={
            "limit": 1,
            "net__gte": f"{year}-01-01T00:00:00Z",
            "net__lt": f"{year + 1}-01-01T00:00:00Z",
        },
        headers=auth_headers(),
        timeout=45,
    )
    response.raise_for_status()
    return int(response.json().get("count", 0))


def update_year(year: int, rows_expected: int, rows_loaded: int) -> None:
    status = "complete" if rows_loaded >= rows_expected else "pending"
    last_offset = rows_expected if status == "complete" else 0
    query = """
    update dev.historical_backfill_state
    set rows_expected = %s,
        rows_loaded = %s,
        last_offset = %s,
        status = %s,
        last_error = null,
        updated_at = %s
    where year = %s;
    """
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (
                    rows_expected,
                    rows_loaded,
                    last_offset,
                    status,
                    datetime.now(timezone.utc),
                    year,
                ),
            )
        conn.commit()


def mark_rate_limited(year: int, error: Exception) -> None:
    query = """
    update dev.historical_backfill_state
    set status = 'rate_limited',
        last_error = %s,
        updated_at = %s
    where year = %s;
    """
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (str(error), datetime.now(timezone.utc), year))
        conn.commit()


def main() -> None:
    ensure_state_table()
    sync_loaded_counts()

    targets = years_to_audit()
    if not targets:
        print("No years to audit.")
        return

    for index, (year, rows_loaded) in enumerate(targets, start=1):
        print(f"Auditing {year} ({index}/{len(targets)})...")
        try:
            rows_expected = fetch_expected_count(year)
        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            if status_code == 429:
                print(f"Rate limited while auditing {year}. Stopping.")
                mark_rate_limited(year, exc)
                return
            raise

        update_year(year, rows_expected, rows_loaded)
        print(f"{year}: loaded={rows_loaded}, expected={rows_expected}")

        if index < len(targets):
            time.sleep(SLEEP_SECONDS)


if __name__ == "__main__":
    main()
