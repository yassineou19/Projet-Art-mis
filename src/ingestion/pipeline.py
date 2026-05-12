"""Pipeline ingestion incremental avec monitoring."""

from datetime import datetime, timezone

from src.database import connection
from src.ingestion.api_client import fetch_launches
from src.ingestion.raw_loader import insert_raw_launches
from src.ingestion.transform import transform_launches


PIPELINE_NAME = "launches_pipeline"
LIMIT = 100


def create_ingestion_run() -> int:
    query = """
    insert into dev.ingestion_runs (
        started_at,
        status
    )
    values (%s, %s)
    returning id;
    """

    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (datetime.now(timezone.utc), "running"))
            run_id = cur.fetchone()[0]
        conn.commit()

    return run_id


def finish_ingestion_run(
    run_id: int,
    status: str,
    rows_raw_upserted: int = 0,
    rows_clean_upserted: int = 0,
    error_message: str | None = None,
) -> None:
    query = """
    update dev.ingestion_runs
    set
        ended_at = %s,
        status = %s,
        rows_raw_upserted = %s,
        rows_clean_upserted = %s,
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
                    rows_raw_upserted,
                    rows_clean_upserted,
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


def run_pipeline() -> None:
    run_id = create_ingestion_run()

    try:
        last_offset = get_last_offset()

        print(f"Offset actuel: {last_offset}")

        payload = fetch_launches(
            limit=LIMIT,
            offset=last_offset,
        )

        results = payload.get("results", [])
        print(f"Lignes API reçues: {len(results)}")

        if not results:
            finish_ingestion_run(
                run_id=run_id,
                status="success",
                rows_raw_upserted=0,
                rows_clean_upserted=0,
            )
            print("Aucune nouvelle donnée.")
            return

        inserted = insert_raw_launches(results)
        print(f"Lignes RAW upsertées: {inserted}")

        transform_launches()

        update_ingestion_state(
            new_offset=last_offset + LIMIT,
            rows_added=inserted,
        )

        finish_ingestion_run(
            run_id=run_id,
            status="success",
            rows_raw_upserted=inserted,
            rows_clean_upserted=inserted,
        )

        print(f"{inserted} lignes RAW ingérées.")

    except Exception as e:
        finish_ingestion_run(
            run_id=run_id,
            status="error",
            error_message=str(e),
        )
        raise