"""Pipeline ingestion incremental."""

from datetime import datetime, timezone
from src.ingestion.transform import transform_launches
from src.database import connection
from src.ingestion.api_client import fetch_launches
from src.ingestion.raw_loader import insert_raw_launches


PIPELINE_NAME = "launches_pipeline"


def get_last_offset() -> int:
    query = """
    select last_offset
    from dev.ingestion_state
    where pipeline_name = %s
    """

    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (PIPELINE_NAME,))
            result = cur.fetchone()

    return result[0]


def update_ingestion_state(new_offset: int, rows_added: int):
    query = """
    update dev.ingestion_state
    set
        last_offset = %s,
        last_run_at = %s,
        total_rows_ingested = total_rows_ingested + %s
    where pipeline_name = %s
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


def run_pipeline():
    limit = 100

    last_offset = get_last_offset()

    payload = fetch_launches(
        limit=limit,
        offset=last_offset,
    )

    results = payload.get("results", [])

    if not results:
        print("Aucune nouvelle donnée.")
        return

    inserted = insert_raw_launches(results)

    transform_launches()

    update_ingestion_state(
        new_offset=last_offset + limit,
        rows_added=inserted,
    )

    print(f"{inserted} lignes RAW ingérées.")
    print(f"Offset actuel: {last_offset}")
    print(f"Lignes API reçues: {len(results)}")
    print(f"Lignes RAW upsertées: {inserted}")