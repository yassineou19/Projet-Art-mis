"""Cockpit ML de risque des lancements."""

from html import escape

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.ml import (
    LABELED_STATUSES,
    explain_prediction,
    predict_outcomes,
    reliability_summary,
    train_outcome_classifier,
)
from src.ml.reports import build_prediction_pdf
from src.ml.storage import (
    FREE_MONTHLY_ANALYSES,
    add_to_watchlist,
    count_monthly_analyses,
    has_analyzed_launch,
    load_prediction_history,
    load_risk_alerts,
    load_watchlist,
    record_analysis,
    remove_from_watchlist,
    save_prediction,
)
from src.profiles import (
    can_access_premium_features,
    can_access_pro_features,
    get_profile_plan,
    get_subscription_plan_label,
)
from src.queries import load_launch_ml_data
from src.ui import (
    format_number,
    get_user_id,
    insight,
    kpi_card,
    page_header,
    render_sidebar,
    require_auth,
    section_title,
    style_plotly,
)


@st.cache_resource(ttl=3600, show_spinner=False)
def load_risk_model():
    return train_outcome_classifier(load_launch_ml_data())


def locked_feature(title: str, text: str, plan: str) -> None:
    st.markdown(
        f"""
        <div class="artemis-card" style="border-style:dashed;opacity:.78;">
            <div class="artemis-eyebrow">{escape(plan)} requis</div>
            <h3 style="margin:.35rem 0;">{escape(title)}</h3>
            <p class="artemis-muted" style="margin:0;">{escape(text)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button(f"Découvrir {plan}", key=f"upgrade_{title}", width="content"):
        st.switch_page("pages/8_Abonnements.py")


def risk_band(score: float, threshold: float) -> tuple[str, bool]:
    if score >= threshold:
        return "Risque élevé", False
    if score >= threshold * 0.55:
        return "Risque modéré", True
    return "Risque faible", True


def display_value(value, fallback: str) -> str:
    return str(value) if pd.notna(value) and value else fallback


user = require_auth()
render_sidebar(user)
profile = st.session_state.get("profile") or {}
plan = get_profile_plan(profile)
plan_label = get_subscription_plan_label(plan)
has_pro = can_access_pro_features(profile)
has_premium = can_access_premium_features(profile)
user_id = get_user_id(user)

page_header(
    title="Risque de lancement",
    subtitle="Décision, fiabilité et signaux de risque pour les prochaines missions.",
    eyebrow="MACHINE LEARNING · RISK INTELLIGENCE",
    badge=plan_label,
)

try:
    launches = load_launch_ml_data()
    model = load_risk_model()
except Exception as exc:
    st.error(f"Impossible de charger le moteur de risque : {exc}")
    st.stop()

launch_dates = pd.to_datetime(launches["launch_date"], errors="coerce", utc=True)
upcoming = launches[
    (~launches["status"].isin(LABELED_STATUSES))
    & (launch_dates >= pd.Timestamp.now(tz="UTC").normalize())
].copy()
upcoming["launch_date"] = launch_dates.loc[upcoming.index]
upcoming = upcoming.sort_values("launch_date")

if upcoming.empty:
    st.warning("Aucun lancement à venir non résolu n'est disponible.")
    st.stop()

analysis_tab, compare_tab, watch_tab, model_tab = st.tabs(
    ["Analyse", "Comparer", "Suivi", "Modèle"]
)

with analysis_tab:
    section_title("Mission à analyser")
    selected_index = st.selectbox(
        "Lancement",
        options=upcoming.index.tolist(),
        format_func=lambda index: (
            f"{upcoming.loc[index, 'launch_date']:%d/%m/%Y} · "
            f"{upcoming.loc[index, 'launch_name']}"
        ),
        key="ml_launch_selector",
    )
    selected_launch = upcoming.loc[[selected_index]]
    selected_launch_id = str(selected_launch.iloc[0]["launch_id"])

    analyses_used = 0
    already_analyzed = False
    if user_id and not has_pro:
        try:
            analyses_used = count_monthly_analyses(user_id)
            already_analyzed = has_analyzed_launch(user_id, selected_launch_id)
        except Exception:
            analyses_used = 0

    can_analyze = has_pro or already_analyzed or analyses_used < FREE_MONTHLY_ANALYSES
    if not has_pro:
        remaining = max(FREE_MONTHLY_ANALYSES - analyses_used, 0)
        st.caption(f"Plan Free : {remaining} analyse(s) restante(s) ce mois-ci.")
        analyze_clicked = st.button(
            "Analyser le risque",
            type="primary",
            disabled=not can_analyze,
            width="content",
        )
        if analyze_clicked:
            st.session_state["ml_free_launch_id"] = selected_launch_id
            if user_id:
                record_analysis(user_id, selected_launch_id)
        show_analysis = already_analyzed or (
            st.session_state.get("ml_free_launch_id") == selected_launch_id
        )
        if not can_analyze:
            locked_feature(
                "Quota mensuel atteint",
                "Les analyses deviennent illimitées avec le plan Pro.",
                "Pro",
            )
    else:
        show_analysis = True

    if show_analysis:
        selected = predict_outcomes(model, selected_launch).iloc[0]
        risk_pct = float(selected["risk_score"]) * 100
        lower_pct = float(selected["risk_lower"]) * 100
        upper_pct = float(selected["risk_upper"]) * 100
        band, band_positive = risk_band(
            float(selected["risk_score"]), model.decision_threshold
        )

        c1, c2, c3 = st.columns(3)
        with c1:
            kpi_card(
                "Décision Artemis",
                str(selected["prediction"]),
                positive=not bool(selected["predicted_failure"]),
            )
        with c2:
            kpi_card("Niveau de risque", band, positive=band_positive)
        with c3:
            agency = selected.get("agency")
            kpi_card(
                "Date prévue",
                f"{selected['launch_date']:%d/%m/%Y}",
                delta=str(agency) if pd.notna(agency) else "Agence inconnue",
            )

        if has_pro:
            p1, p2, p3 = st.columns(3)
            with p1:
                kpi_card("Risque calibré", f"{risk_pct:.1f}%", positive=band_positive)
            with p2:
                kpi_card(
                    "Fourchette empirique",
                    f"{lower_pct:.1f}% - {upper_pct:.1f}%",
                    delta="Intervalle central à 80%",
                    positive=band_positive,
                )
            with p3:
                kpi_card(
                    "Confiance des données",
                    "Élevée" if pd.notna(selected.get("rocket")) else "Limitée",
                    delta=model.model_version,
                )

            rocket_reliability = reliability_summary(launches, selected, "rocket")
            agency_reliability = reliability_summary(launches, selected, "agency")
            section_title("Fiabilité historique")
            r1, r2 = st.columns(2)
            with r1:
                kpi_card(
                    f"Fusée · {rocket_reliability['label']}",
                    f"{rocket_reliability['success_rate'] * 100:.1f}%",
                    delta=(
                        f"{format_number(rocket_reliability['attempts'])} vols · "
                        f"{rocket_reliability['failures']} échecs"
                    ),
                )
            with r2:
                kpi_card(
                    f"Agence · {agency_reliability['label']}",
                    f"{agency_reliability['success_rate'] * 100:.1f}%",
                    delta=(
                        f"{format_number(agency_reliability['attempts'])} vols · "
                        f"{agency_reliability['failures']} échecs"
                    ),
                )

            section_title("Facteurs de la prédiction")
            drivers = explain_prediction(model, selected_launch)
            fig_drivers = px.bar(
                drivers.sort_values("impact"),
                x="signed_impact",
                y="factor",
                orientation="h",
                color="direction",
                color_discrete_map={
                    "Augmente le risque": "#EF4444",
                    "Réduit le risque": "#10B981",
                },
            )
            fig_drivers.update_traces(
                hovertemplate="<b>%{y}</b><br>Contribution %{x:.2f}<extra></extra>"
            )
            style_plotly(fig_drivers, height=360)
            fig_drivers.update_layout(
                xaxis_title="Contribution au score",
                yaxis_title="",
                legend_title_text="",
            )
            st.plotly_chart(fig_drivers, width="stretch")

            export_row = pd.DataFrame(
                [
                    {
                        "launch_id": selected["launch_id"],
                        "launch_name": selected["launch_name"],
                        "launch_date": selected["launch_date"],
                        "agency": selected.get("agency"),
                        "rocket": selected.get("rocket"),
                        "prediction": selected["prediction"],
                        "risk_score": selected["risk_score"],
                        "risk_lower": selected["risk_lower"],
                        "risk_upper": selected["risk_upper"],
                        "model_version": model.model_version,
                    }
                ]
            )
            st.download_button(
                "Exporter l'analyse CSV",
                data=export_row.to_csv(index=False).encode("utf-8"),
                file_name=f"artemis_risk_{selected_launch_id}.csv",
                mime="text/csv",
                width="content",
            )

            if has_premium:
                action1, action2, action3 = st.columns(3)
                with action1:
                    if st.button("Ajouter à la watchlist", width="stretch"):
                        if user_id:
                            add_to_watchlist(user_id, selected_launch_id)
                            save_prediction(user_id, selected, model.model_version)
                            st.success("Mission ajoutée à la watchlist.")
                        else:
                            st.warning("Identifiant utilisateur indisponible.")
                with action2:
                    if st.button("Enregistrer le score", width="stretch"):
                        if user_id:
                            save_prediction(user_id, selected, model.model_version)
                            st.success("Prédiction enregistrée.")
                with action3:
                    pdf = build_prediction_pdf(
                        selected,
                        rocket_reliability,
                        agency_reliability,
                        drivers,
                        model.model_version,
                    )
                    st.download_button(
                        "Télécharger le rapport PDF",
                        data=pdf,
                        file_name=f"artemis_risk_{selected_launch_id}.pdf",
                        mime="application/pdf",
                        width="stretch",
                    )

                section_title("Simulation Premium")
                scenario1, scenario2, scenario3 = st.columns(3)
                with scenario1:
                    scenario_agency = st.selectbox(
                        "Agence",
                        sorted(launches["agency"].dropna().unique().tolist()),
                        index=None,
                        placeholder=display_value(selected.get("agency"), "Agence"),
                    )
                with scenario2:
                    scenario_rocket = st.selectbox(
                        "Fusée",
                        sorted(launches["rocket"].dropna().unique().tolist()),
                        index=None,
                        placeholder=display_value(selected.get("rocket"), "Fusée"),
                    )
                with scenario3:
                    scenario_orbit = st.selectbox(
                        "Orbite",
                        sorted(launches["orbit"].dropna().unique().tolist()),
                        index=None,
                        placeholder=display_value(selected.get("orbit"), "Orbite"),
                    )

                scenario = selected_launch.copy()
                if scenario_agency:
                    scenario.loc[:, "agency"] = scenario_agency
                    agency_rows = launches[launches["agency"] == scenario_agency]
                    scenario.loc[:, "agency_attempts"] = agency_rows[
                        "agency_attempts"
                    ].max()
                if scenario_rocket:
                    scenario.loc[:, "rocket"] = scenario_rocket
                if scenario_orbit:
                    scenario.loc[:, "orbit"] = scenario_orbit
                simulated = predict_outcomes(model, scenario).iloc[0]
                delta = (float(simulated["risk_score"]) - float(selected["risk_score"])) * 100
                insight(
                    f"Scénario : risque estimé à <strong>{simulated['risk_score'] * 100:.1f}%</strong> "
                    f"(<strong>{delta:+.1f} point(s)</strong> par rapport à la mission actuelle)."
                )
                st.caption("Simulation indicative : elle ne remplace pas une étude d'ingénierie.")
            else:
                locked_feature(
                    "Surveillance et simulation",
                    "Watchlist, alertes, scénarios et rapports PDF sont disponibles en Premium.",
                    "Premium",
                )
        else:
            locked_feature(
                "Analyse explicable",
                "Le score exact, la fourchette, la fiabilité et les facteurs sont disponibles en Pro.",
                "Pro",
            )

with compare_tab:
    if has_pro:
        section_title("Comparer les prochaines missions")
        comparison_indices = st.multiselect(
            "Missions",
            options=upcoming.index.tolist(),
            default=upcoming.index.tolist()[:3],
            max_selections=5,
            format_func=lambda index: str(upcoming.loc[index, "launch_name"]),
        )
        if comparison_indices:
            comparison = predict_outcomes(model, upcoming.loc[comparison_indices])
            comparison_table = comparison[
                ["launch_name", "launch_date", "agency", "rocket", "risk_score", "prediction"]
            ].copy()
            comparison_table["risk_score"] = comparison_table["risk_score"] * 100
            st.dataframe(
                comparison_table,
                width="stretch",
                hide_index=True,
                column_config={
                    "launch_name": "Mission",
                    "launch_date": st.column_config.DatetimeColumn("Date", format="DD/MM/YYYY"),
                    "agency": "Agence",
                    "rocket": "Fusée",
                    "risk_score": st.column_config.ProgressColumn(
                        "Risque (%)", min_value=0, max_value=100, format="%.1f%%"
                    ),
                    "prediction": "Décision",
                },
            )
            st.download_button(
                "Exporter la comparaison CSV",
                comparison_table.to_csv(index=False).encode("utf-8"),
                file_name="artemis_launch_comparison.csv",
                mime="text/csv",
            )
    else:
        locked_feature(
            "Comparateur de missions",
            "Comparez jusqu'à cinq lancements et exportez le résultat avec Pro.",
            "Pro",
        )

with watch_tab:
    if has_premium and user_id:
        section_title("Watchlist")
        watchlist = load_watchlist(user_id)
        if watchlist.empty:
            st.info("Ajoutez une mission depuis l'onglet Analyse.")
        else:
            st.dataframe(watchlist, width="stretch", hide_index=True)
            remove_id = st.selectbox(
                "Mission à retirer",
                watchlist["launch_id"].tolist(),
                format_func=lambda launch_id: str(
                    watchlist.loc[watchlist["launch_id"] == launch_id, "launch_name"].iloc[0]
                ),
            )
            remove_col, refresh_col = st.columns(2)
            with remove_col:
                if st.button("Retirer de la watchlist", width="stretch"):
                    remove_from_watchlist(user_id, remove_id)
                    st.rerun()
            with refresh_col:
                if st.button("Actualiser les scores suivis", type="primary", width="stretch"):
                    watched_launches = upcoming[
                        upcoming["launch_id"].isin(watchlist["launch_id"])
                    ]
                    refreshed = predict_outcomes(model, watched_launches)
                    for _, prediction in refreshed.iterrows():
                        save_prediction(user_id, prediction, model.model_version)
                    st.success("Scores actualisés.")

        section_title("Alertes internes")
        alerts = load_risk_alerts(user_id)
        if alerts.empty:
            st.caption("Aucun changement de risque supérieur à 2 points.")
        else:
            for alert in alerts.itertuples(index=False):
                st.warning(
                    f"{alert.launch_name} : variation de {alert.risk_change * 100:+.1f} points."
                )

        section_title("Historique des prédictions")
        history = load_prediction_history(user_id)
        if history.empty:
            st.caption("Aucune prédiction enregistrée.")
        else:
            history_display = history.copy()
            history_display["risk_score"] = history_display["risk_score"] * 100
            st.dataframe(history_display, width="stretch", hide_index=True)
    else:
        locked_feature(
            "Watchlist et alertes",
            "Suivez les changements de risque et conservez l'historique avec Premium.",
            "Premium",
        )

with model_tab:
    if has_premium:
        section_title("Monitoring du modèle")
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            kpi_card("ROC-AUC", f"{model.roc_auc:.3f}")
        with m2:
            kpi_card("PR-AUC", f"{model.average_precision:.3f}")
        with m3:
            kpi_card("Rappel échecs", f"{model.failure_recall * 100:.1f}%")
        with m4:
            kpi_card("Brier score", f"{model.brier_score:.3f}")

        calibration_fig = go.Figure()
        calibration_fig.add_trace(
            go.Scatter(
                x=[0, 0.25], y=[0, 0.25], mode="lines", name="Calibration parfaite",
                line={"color": "#64748B", "dash": "dot"},
            )
        )
        calibration_fig.add_trace(
            go.Scatter(
                x=model.calibration["predicted_risk"],
                y=model.calibration["observed_failure_rate"],
                mode="lines+markers",
                name="Artemis",
                line={"color": "#7C3AED", "width": 3},
            )
        )
        style_plotly(calibration_fig, height=360)
        calibration_fig.update_layout(
            xaxis_title="Risque prédit",
            yaxis_title="Taux d'échec observé",
        )
        st.plotly_chart(calibration_fig, width="stretch")

        confusion = model.confusion
        confusion_fig = go.Figure(
            data=go.Heatmap(
                z=confusion,
                x=["Réussite prédite", "Risque élevé"],
                y=["Réussite réelle", "Échec réel"],
                text=confusion,
                texttemplate="%{text}",
                colorscale=[[0, "#111827"], [1, "#7C3AED"]],
                showscale=False,
            )
        )
        style_plotly(confusion_fig, height=340)
        st.plotly_chart(confusion_fig, width="stretch")
        insight(
            f"Validation temporelle depuis <strong>{model.test_start:%d/%m/%Y}</strong> · "
            f"{format_number(model.training_rows)} lancements · seuil opérationnel "
            f"<strong>{model.decision_threshold * 100:.1f}%</strong>."
        )
    else:
        locked_feature(
            "Transparence avancée du modèle",
            "Calibration, PR-AUC, matrice d'erreur et version du modèle sont disponibles en Premium.",
            "Premium",
        )
