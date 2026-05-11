"""Transformation RAW -> CLEAN."""

from src.database import connection


def transform_launches() -> int:
    """
    Transforme les payloads JSON RAW en table analytique CLEAN.
    """

    query = """
    insert into dev.launches_clean (
        launch_id,
        launch_name,
        launch_date,
        launch_year,
        agency,
        country,
        latitude,
        longitude,
        status
    )
    select
        payload->>'id',
        payload->>'name',
        (payload->>'net')::timestamptz,
        extract(year from (payload->>'net')::timestamptz)::int,
        payload->'launch_service_provider'->>'name',
        coalesce(
            payload->'pad'->'location'->>'country_code',
            payload->'pad'->'location'->>'country',
            'UNKNOWN'
        ),
        nullif(payload->'pad'->>'latitude', '')::numeric,
        nullif(payload->'pad'->>'longitude', '')::numeric,
        payload->'status'->>'name'
    from dev.launches_raw

    on conflict (launch_id)
    do update set
        launch_name = excluded.launch_name,
        launch_date = excluded.launch_date,
        launch_year = excluded.launch_year,
        agency = excluded.agency,
        country = excluded.country,
        latitude = excluded.latitude,
        longitude = excluded.longitude,
        status = excluded.status,
        updated_at = now();
    """

    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)

        conn.commit()

    return 1