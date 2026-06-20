"""Persistance des usages ML, watchlists et prédictions."""

import pandas as pd

from src.database import connection


FREE_MONTHLY_ANALYSES = 3


def count_monthly_analyses(user_id: str) -> int:
    query = """
        select count(distinct launch_id)
        from public.ml_usage_events
        where user_id = %s
          and event_type = 'analysis'
          and created_at >= date_trunc('month', now());
    """
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (user_id,))
            return int(cur.fetchone()[0])


def has_analyzed_launch(user_id: str, launch_id: str) -> bool:
    query = """
        select exists (
            select 1
            from public.ml_usage_events
            where user_id = %s
              and launch_id = %s
              and event_type = 'analysis'
              and created_at >= date_trunc('month', now())
        );
    """
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (user_id, launch_id))
            return bool(cur.fetchone()[0])


def record_analysis(user_id: str, launch_id: str) -> None:
    if has_analyzed_launch(user_id, launch_id):
        return
    query = """
        insert into public.ml_usage_events (user_id, event_type, launch_id)
        values (%s, 'analysis', %s);
    """
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (user_id, launch_id))
        conn.commit()


def load_watchlist(user_id: str) -> pd.DataFrame:
    query = """
        select
            watch.launch_id,
            clean.launch_name,
            clean.launch_date,
            clean.agency,
            watch.created_at
        from public.ml_watchlist as watch
        left join dev.launches_clean as clean using (launch_id)
        where watch.user_id = %s
        order by clean.launch_date nulls last;
    """
    with connection() as conn:
        return pd.read_sql(query, conn, params=(user_id,))


def add_to_watchlist(user_id: str, launch_id: str) -> None:
    query = """
        insert into public.ml_watchlist (user_id, launch_id)
        values (%s, %s)
        on conflict (user_id, launch_id) do nothing;
    """
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (user_id, launch_id))
        conn.commit()


def remove_from_watchlist(user_id: str, launch_id: str) -> None:
    query = """
        delete from public.ml_watchlist
        where user_id = %s and launch_id = %s;
    """
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (user_id, launch_id))
        conn.commit()


def save_prediction(user_id: str, prediction: pd.Series, model_version: str) -> None:
    query = """
        insert into public.ml_prediction_history (
            user_id,
            launch_id,
            launch_name,
            risk_score,
            risk_lower,
            risk_upper,
            prediction,
            model_version
        )
        values (%s, %s, %s, %s, %s, %s, %s, %s);
    """
    values = (
        user_id,
        str(prediction["launch_id"]),
        str(prediction["launch_name"]),
        float(prediction["risk_score"]),
        float(prediction["risk_lower"]),
        float(prediction["risk_upper"]),
        str(prediction["prediction"]),
        model_version,
    )
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, values)
        conn.commit()


def load_prediction_history(user_id: str, limit: int = 100) -> pd.DataFrame:
    query = """
        select
            launch_id,
            launch_name,
            risk_score,
            risk_lower,
            risk_upper,
            prediction,
            model_version,
            created_at
        from public.ml_prediction_history
        where user_id = %s
        order by created_at desc
        limit %s;
    """
    with connection() as conn:
        return pd.read_sql(query, conn, params=(user_id, limit))


def load_risk_alerts(user_id: str, minimum_change: float = 0.02) -> pd.DataFrame:
    query = """
        with ranked as (
            select
                history.*,
                row_number() over (
                    partition by history.launch_id order by history.created_at desc
                ) as rank,
                lead(history.risk_score) over (
                    partition by history.launch_id order by history.created_at desc
                ) as previous_risk
            from public.ml_prediction_history as history
            join public.ml_watchlist as watch
              on watch.user_id = history.user_id
             and watch.launch_id = history.launch_id
            where history.user_id = %s
        )
        select
            launch_id,
            launch_name,
            risk_score,
            previous_risk,
            risk_score - previous_risk as risk_change,
            created_at
        from ranked
        where rank = 1
          and previous_risk is not null
          and abs(risk_score - previous_risk) >= %s
        order by abs(risk_score - previous_risk) desc;
    """
    with connection() as conn:
        return pd.read_sql(query, conn, params=(user_id, minimum_change))
