"""Insertion RAW des payloads API dans Supabase/Postgres."""

import json
from src.database import connection


def insert_raw_launches(results: list[dict]) -> dict:
    """
    Upsert les payloads bruts dans dev.launches_raw.

    Retourne le nombre de lignes traitees, inserees et mises a jour.
    """
    launch_ids = [item["id"] for item in results]

    existing_ids: set[str] = set()
    if launch_ids:
        existing_query = """
        select launch_id
        from dev.launches_raw
        where launch_id = any(%s);
        """

        with connection() as conn:
            with conn.cursor() as cur:
                cur.execute(existing_query, (launch_ids,))
                existing_ids = {row[0] for row in cur.fetchall()}

    query = """
    insert into dev.launches_raw (
        launch_id,
        payload
    )
    values (%s, %s)
    on conflict (launch_id)
    do update set
        payload = excluded.payload,
        ingested_at = now();
    """

    rows = 0

    with connection() as conn:
        with conn.cursor() as cur:
            for item in results:
                cur.execute(
                    query,
                    (
                        item["id"],
                        json.dumps(item),
                    ),
                )

                rows += 1

        conn.commit()

    return {
        "processed": rows,
        "inserted": rows - len(existing_ids),
        "updated": len(existing_ids),
    }
