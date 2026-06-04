"""Pipeline Monitoring — Control Center data engineering."""

from datetime import datetime, timezone

import pandas as pd
import plotly.express as px
import streamlit as st

from src.database import connection
from src.ui import (
    ARTEMIS_COLORS,
    format_number,
    get_theme,
    insight,
    kpi_card,
    page_header,
    render_sidebar,
    require_admin,
    require_auth,
    section_title,
    status_badge,
    style_plotly,
)


user = require_auth()
require_admin(user)
render_sidebar(user)

page_header(
    title="Data Control Center",
    subtitle="Supervision du pipeline, de la couverture historique et de la qualité sémantique.",
    eyebrow="DATA ENGINEERING · CONTROL CENTER",
    badge="Admin",
)


@st.cache_data(ttl=60, show_spinner=False)
def load_pipeline_runs() -> pd.DataFrame:
    query = """
    select id, started_at, ended_at, status, run_type,
           rows_api_received,
           rows_raw_upserted, rows_raw_inserted, rows_raw_updated,
           rows_clean_upserted, rows_clean_inserted, rows_clean_updated,
           error_message
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


@st.cache_data(ttl=60, show_spinner=False)
def load_semantic_health() -> pd.DataFrame:
    with connection() as conn:
        return pd.read_sql("select * from dev_semantic.semantic_health_overview;", conn)


@st.cache_data(ttl=60, show_spinner=False)
def load_data_coverage() -> pd.DataFrame:
    query = """
    select year, backfill_status, coverage_category, backfill_priority,
           rows_loaded, rows_expected, rows_missing, coverage_pct,
           is_complete, has_launch_data, backfill_updated_at
    from dev_semantic.data_coverage_by_year
    order by year;
    """
    with connection() as conn:
        return pd.read_sql(query, conn)


@st.cache_data(ttl=60, show_spinner=False)
def load_data_quality_summary() -> pd.DataFrame:
    with connection() as conn:
        return pd.read_sql("select * from dev_semantic.data_quality_summary;", conn)


@st.cache_data(ttl=60, show_spinner=False)
def load_data_quality_by_year() -> pd.DataFrame:
    with connection() as conn:
        return pd.read_sql("select * from dev_semantic.data_quality_by_year;", conn)


@st.cache_data(ttl=60, show_spinner=False)
def load_backfill_priority_queue() -> pd.DataFrame:
    with connection() as conn:
        return pd.read_sql("select * from dev_semantic.backfill_priority_queue limit 50;", conn)


def _fmt_duration(seconds) -> str:
    if seconds is None or pd.isna(seconds):
        return "—"
    if seconds < 60:
        return f"{seconds:.1f} s"
    return f"{seconds / 60:.1f} min"


def _last_run_label(latest_run: pd.Series | None) -> str:
    if latest_run is None or pd.isna(latest_run["started_at"]):
        return "—"

    last_dt = pd.to_datetime(latest_run["started_at"])
    if last_dt.tzinfo is None:
        last_dt = last_dt.tz_localize("UTC")

    delta = datetime.now(timezone.utc) - last_dt.to_pydatetime()
    mins = int(delta.total_seconds() / 60)
    if mins < 60:
        return f"il y a {mins} min"
    if mins < 60 * 24:
        return f"il y a {mins // 60} h"
    return f"il y a {mins // (60 * 24)} j"


def _pipeline_success_rate(runs: pd.DataFrame) -> float:
    if runs.empty:
        return 0.0

    health_runs = runs[runs["status"] != "rate_limited"]
    success_count = int((health_runs["status"] == "success").sum())
    return (success_count / len(health_runs)) * 100 if not health_runs.empty else 100


def _avg_duration(runs: pd.DataFrame) -> float | None:
    runs_with_duration = runs.dropna(subset=["started_at", "ended_at"]).copy()
    if runs_with_duration.empty:
        return None

    runs_with_duration["started_at"] = pd.to_datetime(runs_with_duration["started_at"])
    runs_with_duration["ended_at"] = pd.to_datetime(runs_with_duration["ended_at"])
    durations = (runs_with_duration["ended_at"] - runs_with_duration["started_at"]).dt.total_seconds()
    return float(durations.mean()) if not durations.empty else None


def _status_class(success_rate: float) -> tuple[str, str]:
    if success_rate >= 90:
        return "Healthy", "success"
    if success_rate >= 70:
        return "Warning", "warning"
    return "Degraded", "danger"


def render_pipeline_tab(
    runs: pd.DataFrame,
    state: pd.DataFrame,
    freshness: pd.DataFrame,
) -> None:
    latest_run = runs.iloc[0] if not runs.empty else None
    fresh = freshness.iloc[0] if not freshness.empty else None
    state_row = state.iloc[0] if not state.empty else None
    success_rate = _pipeline_success_rate(runs)
    avg_duration_s = _avg_duration(runs)
    last_run_ago = _last_run_label(latest_run)

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
        health_label, health_cls = _status_class(success_rate)
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

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Total launches", format_number(fresh["total_launches"]) if fresh is not None else "0")
    with c2:
        value = str(int(fresh["max_year"])) if fresh is not None and pd.notna(fresh["max_year"]) else "—"
        kpi_card("Dernière année", value)
    with c3:
        kpi_card("Offset actuel", format_number(state_row["last_offset"]) if state_row is not None else "0")
    with c4:
        kpi_card("Durée moyenne run", _fmt_duration(avg_duration_s))

    if latest_run is not None:
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            kpi_card("API reçues", format_number(latest_run.get("rows_api_received", 0)))
        with m2:
            kpi_card("RAW nouvelles", format_number(latest_run.get("rows_raw_inserted", 0)))
        with m3:
            kpi_card("RAW mises à jour", format_number(latest_run.get("rows_raw_updated", 0)))
        with m4:
            kpi_card("CLEAN nouvelles", format_number(latest_run.get("rows_clean_inserted", 0)))

    st.divider()

    rate_limited = runs[runs["status"] == "rate_limited"] if not runs.empty else pd.DataFrame()
    errors = runs[runs["status"].isin(["error", "failed"])] if not runs.empty else pd.DataFrame()

    if not rate_limited.empty:
        section_title("Quota API")
        st.markdown(
            f"""
            <div class="artemis-card" style="border-left: 3px solid var(--warning);">
                <div style="display:flex; align-items:center; gap:.6rem;">
                    <span class="artemis-status warning"><span class="dot"></span>{len(rate_limited)} rate limit</span>
                    <span class="artemis-muted">
                        The Space Devs a temporairement limité les appels API. Le backfill reprendra plus tard.
                    </span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

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
        st.dataframe(errors[["started_at", "error_message"]], use_container_width=True, hide_index=True)

    section_title("Historique des runs")
    if not runs.empty:
        runs_chart = runs.copy()
        runs_chart["started_at"] = pd.to_datetime(runs_chart["started_at"])
        theme = get_theme()

        fig = px.line(
            runs_chart.sort_values("started_at"),
            x="started_at",
            y=["rows_raw_inserted", "rows_raw_updated"],
            markers=True,
            labels={"started_at": "Run time", "value": "Rows", "variable": "Metric"},
            color_discrete_sequence=[theme["success"], theme["cyan"]],
        )
        fig.update_traces(line=dict(width=2.5), marker=dict(size=7))
        style_plotly(fig, height=320)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aucun run enregistré.")

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
                "run_type": st.column_config.TextColumn("Type"),
                "rows_api_received": st.column_config.NumberColumn("API"),
                "rows_raw_upserted": st.column_config.NumberColumn("RAW traitées"),
                "rows_raw_inserted": st.column_config.NumberColumn("RAW nouvelles"),
                "rows_raw_updated": st.column_config.NumberColumn("RAW updates"),
                "rows_clean_upserted": st.column_config.NumberColumn("CLEAN traitées"),
                "rows_clean_inserted": st.column_config.NumberColumn("CLEAN nouvelles"),
                "rows_clean_updated": st.column_config.NumberColumn("CLEAN updates"),
                "error_message": st.column_config.TextColumn("Error"),
            },
        )

    if latest_run is not None and latest_run["status"] == "success":
        rows_inserted = int(latest_run["rows_raw_inserted"]) if pd.notna(latest_run["rows_raw_inserted"]) else 0
        rows_updated = int(latest_run["rows_raw_updated"]) if pd.notna(latest_run["rows_raw_updated"]) else 0
        insight(
            f"Pipeline opérationnel. Dernier run réussi avec "
            f"<strong>{format_number(rows_inserted)}</strong> nouvelles lignes RAW "
            f"et <strong>{format_number(rows_updated)}</strong> mises à jour."
        )


def render_quality_tab(
    health: pd.DataFrame,
    coverage: pd.DataFrame,
    quality_summary: pd.DataFrame,
    quality_by_year: pd.DataFrame,
    priority_queue: pd.DataFrame,
) -> None:
    health_row = health.iloc[0] if not health.empty else None
    quality_row = quality_summary.iloc[0] if not quality_summary.empty else None

    section_title("Santé sémantique")

    h1, h2, h3, h4 = st.columns(4)
    with h1:
        kpi_card("Années complètes", format_number(health_row["complete_years"]) if health_row is not None else "0")
    with h2:
        kpi_card(
            "À auditer",
            format_number(health_row["years_loaded_not_audited"]) if health_row is not None else "0",
        )
    with h3:
        kpi_card("Années inconnues", format_number(health_row["pending_years"]) if health_row is not None else "0")
    with h4:
        value = format_number(health_row["launches_in_complete_years"]) if health_row is not None else "0"
        kpi_card("Launches fiables ML", value)

    q1, q2, q3, q4 = st.columns(4)
    with q1:
        kpi_card(
            "Coordonnées manquantes",
            format_number(quality_row["missing_coordinates"]) if quality_row is not None else "0",
        )
    with q2:
        kpi_card("Agences manquantes", format_number(quality_row["missing_agency"]) if quality_row is not None else "0")
    with q3:
        kpi_card("Pays manquants", format_number(quality_row["missing_country"]) if quality_row is not None else "0")
    with q4:
        kpi_card(
            "Statuts non classés",
            format_number(quality_row["other_status_category"]) if quality_row is not None else "0",
        )

    if health_row is not None:
        total_launches = int(health_row["total_launches"])
        reliable_launches = int(health_row["launches_in_complete_years"])
        reliable_pct = (reliable_launches / total_launches * 100) if total_launches else 0
        insight(
            f"La base contient <strong>{format_number(total_launches)}</strong> lancements. "
            f"<strong>{format_number(reliable_launches)}</strong> sont dans des années auditées complètes "
            f"({reliable_pct:.1f}%)."
        )

    st.divider()
    section_title("Couverture historique")

    if not coverage.empty:
        category_order = ["complete", "partial", "missing", "audit_needed", "unknown", "review"]
        category_colors = {
            "complete": ARTEMIS_COLORS["success"],
            "partial": ARTEMIS_COLORS["warning"],
            "missing": ARTEMIS_COLORS["danger"],
            "audit_needed": ARTEMIS_COLORS["cyan"],
            "unknown": ARTEMIS_COLORS["muted"],
            "review": ARTEMIS_COLORS["purple"],
        }

        fig = px.bar(
            coverage,
            x="year",
            y="rows_loaded",
            color="coverage_category",
            category_orders={"coverage_category": category_order},
            color_discrete_map=category_colors,
            labels={
                "year": "Année",
                "rows_loaded": "Launches chargés",
                "coverage_category": "Couverture",
            },
            hover_data=["rows_expected", "coverage_pct", "backfill_status"],
        )
        style_plotly(fig, height=360)
        st.plotly_chart(fig, use_container_width=True)

        summary = (
            coverage.groupby("coverage_category", as_index=False)
            .agg(years=("year", "count"), rows_loaded=("rows_loaded", "sum"))
            .sort_values("coverage_category")
        )
        st.dataframe(
            summary,
            use_container_width=True,
            hide_index=True,
            column_config={
                "coverage_category": st.column_config.TextColumn("Catégorie"),
                "years": st.column_config.NumberColumn("Années"),
                "rows_loaded": st.column_config.NumberColumn("Launches chargés"),
            },
        )

    section_title("Priorité backfill")
    if priority_queue.empty:
        st.success("Toutes les années suivies sont complètes.")
    else:
        st.dataframe(
            priority_queue,
            use_container_width=True,
            hide_index=True,
            column_config={
                "year": st.column_config.NumberColumn("Année", width="small"),
                "backfill_status": st.column_config.TextColumn("Statut"),
                "coverage_category": st.column_config.TextColumn("Catégorie"),
                "backfill_priority": st.column_config.NumberColumn("Priorité"),
                "rows_loaded": st.column_config.NumberColumn("Chargées"),
                "rows_expected": st.column_config.NumberColumn("Attendues"),
                "rows_missing": st.column_config.NumberColumn("Manquantes"),
                "coverage_pct": st.column_config.NumberColumn("Couverture %", format="%.2f"),
            },
        )

    section_title("Qualité par année")
    if not quality_by_year.empty:
        fig_quality = px.line(
            quality_by_year,
            x="year",
            y=["missing_coordinates", "missing_agency", "missing_country", "other_status_category"],
            markers=True,
            labels={"year": "Année", "value": "Lignes", "variable": "Contrôle"},
            color_discrete_sequence=[
                ARTEMIS_COLORS["cyan"],
                ARTEMIS_COLORS["warning"],
                ARTEMIS_COLORS["danger"],
                ARTEMIS_COLORS["purple"],
            ],
        )
        style_plotly(fig_quality, height=320)
        st.plotly_chart(fig_quality, use_container_width=True)

        st.dataframe(
            quality_by_year.sort_values("year"),
            use_container_width=True,
            hide_index=True,
            column_config={
                "year": st.column_config.NumberColumn("Année", width="small"),
                "launches": st.column_config.NumberColumn("Launches"),
                "launches_in_complete_years": st.column_config.NumberColumn("Launches années complètes"),
                "missing_agency": st.column_config.NumberColumn("Agences manquantes"),
                "missing_country": st.column_config.NumberColumn("Pays manquants"),
                "missing_coordinates": st.column_config.NumberColumn("Coord. manquantes"),
                "missing_status": st.column_config.NumberColumn("Statuts manquants"),
                "other_status_category": st.column_config.NumberColumn("Statuts non classés"),
                "missing_coordinates_pct": st.column_config.NumberColumn("Coord. manquantes %", format="%.2f"),
                "is_complete_year": st.column_config.CheckboxColumn("Année complète"),
            },
        )


try:
    runs = load_pipeline_runs()
    state = load_pipeline_state()
    freshness = load_data_freshness()
    semantic_health = load_semantic_health()
    data_coverage = load_data_coverage()
    data_quality_summary = load_data_quality_summary()
    data_quality_by_year = load_data_quality_by_year()
    backfill_priority_queue = load_backfill_priority_queue()
except Exception as e:
    st.error(f"Impossible de charger les données : {e}")
    st.stop()


pipeline_tab, quality_tab = st.tabs(["Pipeline", "Data Quality"])

with pipeline_tab:
    render_pipeline_tab(runs, state, freshness)

with quality_tab:
    render_quality_tab(
        semantic_health,
        data_coverage,
        data_quality_summary,
        data_quality_by_year,
        backfill_priority_queue,
    )
