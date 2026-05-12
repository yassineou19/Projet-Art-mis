"""Monitoring du pipeline d'ingestion Artemis."""

import streamlit as st
import pandas as pd
import plotly.express as px

from src.ui import require_auth, require_admin, render_sidebar, page_header
from src.database import connection
from src.ui import (
    require_auth,
    require_admin,
    render_sidebar,
    page_header,
    kpi_card,
    style_plotly,
    insight,
)


user = require_auth()
require_admin(user)
render_sidebar(user)


page_header(
    title="Pipeline Monitoring",
    subtitle="Suivi du pipeline ingestion, qualité et fraîcheur des données.",
    eyebrow="DATA ENGINEERING · MONITORING",
)


@st.cache_data(ttl=60, show_spinner=False)
def load_pipeline_runs() -> pd.DataFrame:
    query = """
    select
        id,
        started_at,
        ended_at,
        status,
        rows_raw_upserted,
        rows_clean_upserted,
        error_message
    from dev.ingestion_runs
    order by started_at desc
    limit 100;
    """

    with connection() as conn:
        return pd.read_sql(query, conn)


@st.cache_data(ttl=60, show_spinner=False)
def load_pipeline_state() -> pd.DataFrame:
    query = """
    select *
    from dev.ingestion_state;
    """

    with connection() as conn:
        return pd.read_sql(query, conn)


@st.cache_data(ttl=60, show_spinner=False)
def load_data_freshness() -> pd.DataFrame:
    query = """
    select
        count(*) as total_launches,
        min(launch_year) as min_year,
        max(launch_year) as max_year
    from dev.launches_clean;
    """

    with connection() as conn:
        return pd.read_sql(query, conn)


runs = load_pipeline_runs()
state = load_pipeline_state()
freshness = load_data_freshness()


latest_run = runs.iloc[0] if not runs.empty else None
fresh = freshness.iloc[0] if not freshness.empty else None
state_row = state.iloc[0] if not state.empty else None


c1, c2, c3, c4 = st.columns(4)

with c1:
    kpi_card(
        "Total launches",
        f"{int(fresh['total_launches']):,}" if fresh is not None else "0",
    )

with c2:
    kpi_card(
        "Dernière année",
        f"{int(fresh['max_year'])}" if fresh is not None else "—",
    )

with c3:
    kpi_card(
        "Offset actuel",
        f"{int(state_row['last_offset'])}" if state_row is not None else "0",
    )

with c4:
    kpi_card(
        "Dernier statut",
        latest_run['status'] if latest_run is not None else "unknown",
    )


st.divider()


st.subheader("📈 Historique des runs")

if not runs.empty:
    runs_chart = runs.copy()
    runs_chart['started_at'] = pd.to_datetime(runs_chart['started_at'])

    fig = px.line(
        runs_chart.sort_values('started_at'),
        x='started_at',
        y='rows_raw_upserted',
        markers=True,
        labels={
            'started_at': 'Run time',
            'rows_raw_upserted': 'Rows ingested',
        },
    )

    style_plotly(fig, height=350)
    st.plotly_chart(fig, use_container_width=True)


st.subheader("📋 Derniers runs")

st.dataframe(
    runs,
    use_container_width=True,
    hide_index=True,
)


if latest_run is not None and latest_run['status'] == 'success':
    insight(
        f"Le pipeline fonctionne correctement. Dernier run réussi avec "
        f"<strong>{int(latest_run['rows_raw_upserted'])}</strong> lignes ingérées."
    )


errors = runs[runs['status'] == 'error'] if not runs.empty else pd.DataFrame()

if not errors.empty:
    st.subheader("⚠️ Dernières erreurs")
    st.dataframe(
        errors[[
            'started_at',
            'error_message',
        ]],
        use_container_width=True,
        hide_index=True,
    )