"""Pipeline Monitoring — Control Center data engineering."""

from datetime import datetime, timezone

import streamlit as st
import pandas as pd
import plotly.express as px

from src.database import connection
from src.ui import (
    require_auth, require_admin, render_sidebar, page_header,
    kpi_card, style_plotly, insight, status_badge, section_title,
    format_number, get_theme,
)

user = require_auth()
require_admin(user)
render_sidebar(user)

page_header(
    title="Pipeline Monitoring",
    subtitle="Supervision du pipeline d'ingestion, qualité et fraîcheur des données.",
    eyebrow="DATA ENGINEERING · CONTROL CENTER",
    badge="Admin",
)


# =========================================================
# QUERIES (inchangées)
# =========================================================

@st.cache_data(ttl=60, show_spinner=False)
def load_pipeline_runs() -> pd.DataFrame:
    query = """
    select id, started_at, ended_at, status,
           rows_raw_upserted, rows_clean_upserted, error_message
    from dev.ingestion_runs
    order by started_at desc
    limit 100;
    """
    with connection() as conn:
        return pd.read_sql(query, conn)


@st.cache_data(ttl=60, show_spinner=False)
def load_pipeline_state() -> pd.DataFrame:
    with connection() as conn:
        return pd.read_sql("select * from dev.ingestion_state;", conn)


@st.cache_data(ttl=60, show_spinner=False)
def load_data_freshness() -> pd.DataFrame:
    query = """
    select count(*) as total_launches,
           min(launch_year) as min_year,
           max(launch_year) as max_year
    from dev.launches_clean;
    """
    with connection() as conn:
        return pd.read_sql(query, conn)


try:
    runs = load_pipeline_runs()
    state = load_pipeline_state()
    freshness = load_data_freshness()
except Exception as e:
    st.error(f"Impossible de charger les données : {e}")
    st.stop()

latest_run = runs.iloc[0] if not runs.empty else None
fresh = freshness.iloc[0] if not freshness.empty else None
state_row = state.iloc[0] if not state.empty else None


# =========================================================
# CALCULS
# =========================================================

success_rate = 0.0
avg_duration_s = None
last_run_ago = "—"

if not runs.empty:
    success_count = int((runs["status"] == "success").sum())
    success_rate = (success_count / len(runs)) * 100

    runs_with_duration = runs.dropna(subset=["started_at", "ended_at"]).copy()
    if not runs_with_duration.empty:
        runs_with_duration["started_at"] = pd.to_datetime(runs_with_duration["started_at"])
        runs_with_duration["ended_at"] = pd.to_datetime(runs_with_duration["ended_at"])
        durations = (runs_with_duration["ended_at"] - runs_with_duration["started_at"]).dt.total_seconds()
        if not durations.empty:
            avg_duration_s = float(durations.mean())

    if latest_run is not None and pd.notna(latest_run["started_at"]):
        last_dt = pd.to_datetime(latest_run["started_at"])
        if last_dt.tzinfo is None:
            last_dt = last_dt.tz_localize("UTC")
        delta = datetime.now(timezone.utc) - last_dt.to_pydatetime()
        mins = int(delta.total_seconds() / 60)
        if mins < 60:
            last_run_ago = f"il y a {mins} min"
        elif mins < 60 * 24:
            last_run_ago = f"il y a {mins // 60} h"
        else:
            last_run_ago = f"il y a {mins // (60 * 24)} j"


def _fmt_duration(seconds) -> str:
    if seconds is None or pd.isna(seconds):
        return "—"
    if seconds < 60:
        return f"{seconds:.1f} s"
    return f"{seconds / 60:.1f} min"


# =========================================================
# HEALTH CARDS
# =========================================================

section_title("État du pipeline")

s1, s2 = st.columns(2)

with s1:
    latest_status = str(latest_run["status"]) if latest_run is not None else "unknown"
    st.markdown(
        f"""
        <div class="artemis-card">
            <div style="display:flex; align-items:center; justify-content:space-between;">
                <div>
                    <div class="artemis-eyebrow">Dernière exécution</div>
                    <div style="font-size:1.4rem; font-weight:700; margin-top:.3rem;">{last_run_ago}</div>
                </div>
                {status_badge(latest_status)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with s2:
    if success_rate >= 90:
        health_label, health_cls = "Healthy", "success"
    elif success_rate >= 70:
        health_label, health_cls = "Warning", "warning"
    else:
        health_label, health_cls = "Degraded", "danger"
    st.markdown(
        f"""
        <div class="artemis-card">
            <div style="display:flex; align-items:center; justify-content:space-between;">
                <div>
                    <div class="artemis-eyebrow">Health</div>
                    <div style="font-size:1.4rem; font-weight:700; margin-top:.3rem;">
                        {success_rate:.0f}% de succès
                    </div>
                </div>
                <span class="artemis-status {health_cls}">
                    <span class="dot"></span>{health_label}
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("")

# =========================================================
# KPIs
# =========================================================

c1, c2, c3, c4 = st.columns(4)
with c1:
    kpi_card(
        "Total launches",
        format_number(fresh["total_launches"]) if fresh is not None else "0",
    )
with c2:
    kpi_card(
        "Dernière année",
        str(int(fresh["max_year"])) if fresh is not None and pd.notna(fresh["max_year"]) else "—",
    )
with c3:
    kpi_card(
        "Offset actuel",
        format_number(state_row["last_offset"]) if state_row is not None else "0",
    )
with c4:
    kpi_card("Durée moyenne run", _fmt_duration(avg_duration_s))

st.divider()

# =========================================================
# ALERTES
# =========================================================

errors = runs[runs["status"] == "error"] if not runs.empty else pd.DataFrame()

if not errors.empty:
    section_title("Alertes")
    st.markdown(
        f"""
        <div class="artemis-card" style="border-left: 3px solid var(--danger);">
            <div style="display:flex; align-items:center; gap:.6rem;">
                <span class="artemis-status danger"><span class="dot"></span>{len(errors)} erreur(s)</span>
                <span class="artemis-muted">détectée(s) sur les 100 derniers runs</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.dataframe(
        errors[["started_at", "error_message"]],
        use_container_width=True,
        hide_index=True,
    )

# =========================================================
# TIMELINE
# =========================================================

section_title("Historique des runs")

if not runs.empty:
    runs_chart = runs.copy()
    runs_chart["started_at"] = pd.to_datetime(runs_chart["started_at"])
    theme = get_theme()

    fig = px.line(
        runs_chart.sort_values("started_at"),
        x="started_at", y="rows_raw_upserted",
        markers=True,
        labels={"started_at": "Run time", "rows_raw_upserted": "Rows ingested"},
        color_discrete_sequence=[theme["cyan"]],
    )
    fig.update_traces(line=dict(width=2.5), marker=dict(size=7))
    style_plotly(fig, height=320)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Aucun run enregistré.")

# =========================================================
# TABLE
# =========================================================

section_title("Derniers runs")

if not runs.empty:
    st.dataframe(
        runs,
        use_container_width=True,
        hide_index=True,
        column_config={
            "id": st.column_config.NumberColumn("ID", width="small"),
            "started_at": st.column_config.DatetimeColumn("Started", format="DD/MM HH:mm"),
            "ended_at": st.column_config.DatetimeColumn("Ended", format="DD/MM HH:mm"),
            "status": st.column_config.TextColumn("Status"),
            "rows_raw_upserted": st.column_config.NumberColumn("RAW rows"),
            "rows_clean_upserted": st.column_config.NumberColumn("CLEAN rows"),
            "error_message": st.column_config.TextColumn("Error"),
        },
    )

if latest_run is not None and latest_run["status"] == "success":
    rows_raw = int(latest_run["rows_raw_upserted"]) if pd.notna(latest_run["rows_raw_upserted"]) else 0
    insight(
        f"Pipeline opérationnel. Dernier run réussi avec "
        f"<strong>{format_number(rows_raw)}</strong> lignes ingérées."
    )