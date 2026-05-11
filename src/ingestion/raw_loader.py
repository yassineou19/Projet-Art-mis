"""Insertion RAW des payloads API dans Supabase/Postgres."""

import json
from src.database import connection


def insert_raw_launches(results: list[dict]) -> int:
    """
    Upsert les payloads bruts dans dev.launches_raw.

    Retourne le nombre de lignes traitées.
    """

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

    return rows