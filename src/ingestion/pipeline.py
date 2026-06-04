"""Pipeline ingestion incremental avec monitoring."""

from datetime import datetime, timezone

import requests

from src.database import connection
from src.ingestion.api_client import (
    fetch_launches,
    fetch_previous_launches,
    fetch_upcoming_launches,
)
from src.ingestion.raw_loader import insert_raw_launches
from src.ingestion.transform import transform_launches


PIPELINE_NAME = "launches_pipeline"
LIMIT = 100
RECENT_LIMIT = 100


def is_rate_limit_error(error: Exception) -> bool:
    """Retourne True si l'API The Space Devs renvoie une limite de débit."""
    return (
        isinstance(error, requests.HTTPError)
        and error.response is not None
        and error.response.status_code == 429
    )


def create_ingestion_run(run_type: str = "backfill") -> int:
    query = """
    insert into dev.ingestion_runs (
        started_at,
        status,
        run_type
    )
    values (%s, %s, %s)
    returning id;
    """

    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (datetime.now(timezone.utc), "running", run_type))
            run_id = cur.fetchone()[0]
        conn.commit()

    return run_id


def finish_ingestion_run(
    run_id: int,
    status: str,
    rows_api_received: int = 0,
    rows_raw_upserted: int = 0,
    rows_clean_upserted: int = 0,
    rows_raw_inserted: int = 0,
    rows_raw_updated: int = 0,
    rows_clean_inserted: int = 0,
    rows_clean_updated: int = 0,
    error_message: str | None = None,
) -> None:
    query = """
    update dev.ingestion_runs
    set
        ended_at = %s,
        status = %s,
        rows_api_received = %s,
        rows_raw_upserted = %s,
        rows_clean_upserted = %s,
        rows_raw_inserted = %s,
        rows_raw_updated = %s,
        rows_clean_inserted = %s,
        rows_clean_updated = %s,
        error_message = %s
    where id = %s;
    """

    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (
                    datetime.now(timezone.utc),
                    status,
                    rows_api_received,
                    rows_raw_upserted,
                    rows_clean_upserted,
                    rows_raw_inserted,
                    rows_raw_updated,
                    rows_clean_inserted,
                    rows_clean_updated,
                    error_message,
                    run_id,
                ),
            )
        conn.commit()


def get_last_offset() -> int:
    query = """
    select last_offset
    from dev.ingestion_state
    where pipeline_name = %s;
    """

    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (PIPELINE_NAME,))
            result = cur.fetchone()

    if result is None:
        raise RuntimeError(f"Pipeline state introuvable: {PIPELINE_NAME}")

    return result[0]


def count_existing_clean_launches(launch_ids: list[str]) -> int:
    """Compte les launch_id deja presents dans la table CLEAN."""
    if not launch_ids:
        return 0

    query = """
    select count(*)
    from dev.launches_clean
    where launch_id = any(%s);
    """

    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (launch_ids,))
            return cur.fetchone()[0]


def update_ingestion_state(new_offset: int, rows_added: int) -> None:
    query = """
    update dev.ingestion_state
    set
        last_offset = %s,
        last_run_at = %s,
        total_rows_ingested = total_rows_ingested + %s
    where pipeline_name = %s;
    """

    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (
                    new_offset,
                    datetime.now(timezone.utc),
                    rows_added,
                    PIPELINE_NAME,
                ),
            )
        conn.commit()


def increment_ingestion_total(rows_added: int) -> None:
    """Incrémente le total ingéré sans toucher à l'offset du backfill."""
    query = """
    update dev.ingestion_state
    set
        last_run_at = %s,
        total_rows_ingested = total_rows_ingested + %s
    where pipeline_name = %s;
    """

    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (
                    datetime.now(timezone.utc),
                    rows_added,
                    PIPELINE_NAME,
                ),
            )
        conn.commit()


def _dedupe_launches(results: list[dict]) -> list[dict]:
    """Déduplique les lancements par id en conservant le dernier payload reçu."""
    by_id = {}
    for item in results:
        by_id[item["id"]] = item
    return list(by_id.values())


def process_launch_results(
    run_id: int,
    results: list[dict],
    update_offset_to: int | None = None,
) -> dict:
    """Upsert RAW, transforme CLEAN, journalise les compteurs du run."""
    rows_api_received = len(results)
    print(f"Lignes API reçues: {rows_api_received}")

    if not results:
        finish_ingestion_run(
            run_id=run_id,
            status="success",
            rows_api_received=0,
            rows_raw_upserted=0,
            rows_clean_upserted=0,
        )
        print("Aucune nouvelle donnée.")
        return {
            "api_received": 0,
            "raw_inserted": 0,
            "raw_updated": 0,
            "clean_inserted": 0,
            "clean_updated": 0,
        }

    launch_ids = [item["id"] for item in results]
    clean_existing = count_existing_clean_launches(launch_ids)

    raw_stats = insert_raw_launches(results)
    print(
        "Lignes RAW: "
        f"{raw_stats['inserted']} nouvelles, "
        f"{raw_stats['updated']} mises à jour "
        f"({raw_stats['processed']} traitées)"
    )

    transform_launches()

    clean_inserted = rows_api_received - clean_existing
    clean_updated = clean_existing

    if update_offset_to is not None:
        update_ingestion_state(
            new_offset=update_offset_to,
            rows_added=raw_stats["inserted"],
        )
    else:
        increment_ingestion_total(raw_stats["inserted"])

    finish_ingestion_run(
        run_id=run_id,
        status="success",
        rows_api_received=rows_api_received,
        rows_raw_upserted=raw_stats["processed"],
        rows_clean_upserted=rows_api_received,
        rows_raw_inserted=raw_stats["inserted"],
        rows_raw_updated=raw_stats["updated"],
        rows_clean_inserted=clean_inserted,
        rows_clean_updated=clean_updated,
    )

    print(
        "Ingestion terminée: "
        f"{raw_stats['inserted']} nouvelles lignes RAW, "
        f"{raw_stats['updated']} lignes RAW mises à jour."
    )

    return {
        "api_received": rows_api_received,
        "raw_inserted": raw_stats["inserted"],
        "raw_updated": raw_stats["updated"],
        "clean_inserted": clean_inserted,
        "clean_updated": clean_updated,
    }


def run_pipeline() -> None:
    run_id = create_ingestion_run(run_type="backfill")

    try:
        last_offset = get_last_offset()

        print(f"Offset actuel: {last_offset}")

        payload = fetch_launches(
            limit=LIMIT,
            offset=last_offset,
        )

        results = payload.get("results", [])
        process_launch_results(
            run_id=run_id,
            results=results,
            update_offset_to=last_offset + len(results),
        )

    except Exception as e:
        if is_rate_limit_error(e):
            finish_ingestion_run(
                run_id=run_id,
                status="rate_limited",
                error_message=str(e),
            )
            raise

        finish_ingestion_run(
            run_id=run_id,
            status="error",
            error_message=str(e),
        )
        raise


def run_recent_pipeline() -> None:
    """Synchronise les lancements récents et à venir sans avancer l'offset historique."""
    run_id = create_ingestion_run(run_type="recent")

    try:
        previous_payload = fetch_previous_launches(limit=RECENT_LIMIT)
        upcoming_payload = fetch_upcoming_launches(limit=RECENT_LIMIT)

        previous_results = previous_payload.get("results", [])
        upcoming_results = upcoming_payload.get("results", [])
        results = _dedupe_launches(previous_results + upcoming_results)

        print(
            "Sync récent: "
            f"{len(previous_results)} précédents, "
            f"{len(upcoming_results)} à venir, "
            f"{len(results)} uniques."
        )

        process_launch_results(run_id=run_id, results=results)

    except Exception as e:
        if is_rate_limit_error(e):
            finish_ingestion_run(
                run_id=run_id,
                status="rate_limited",
                error_message=str(e),
            )
            raise

        finish_ingestion_run(
            run_id=run_id,
            status="error",
            error_message=str(e),
        )
        raise
