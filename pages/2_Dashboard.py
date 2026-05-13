"""Dashboard principal — KPIs calculés, évolution, top agences, pays, croissance."""
import streamlit as st
from src.ui import plotly_legend_style
import plotly.express as px
import pandas as pd
from src.queries import load_dashboard_data, load_view
from src.ui import (
    require_auth, render_sidebar, page_header,
    kpi_card, insight, style_plotly, ARTEMIS_COLORS,
)

# Auth + sidebar centralisés
user = require_auth()
render_sidebar(user)

# En-tête
page_header(
    title="Dashboard des lancements spatiaux",
    subtitle="Vue d'ensemble de l'activité mondiale: volume, croissance, leaders.",
    eyebrow="ANALYTICS · OVERVIEW",
)

if st.button("Actualiser les données", use_container_width=False):
    st.cache_data.clear()
    st.rerun()

# Chargement avec gestion d'erreur
try:
    data = load_dashboard_data()
except Exception as e:
    st.error(f"Impossible de charger les données: {e}")
    st.stop()

launches_by_year = data["launches_by_year"]
top_agencies = data["top_agencies"]
launches_by_country = data["launches_by_country"]
growth = data["growth"]

# ----- Filtre période -----
years_available = sorted(launches_by_year["year"].dropna().unique().tolist())
if years_available:
    min_y, max_y = int(min(years_available)), int(max(years_available))
    y_from, y_to = st.slider(
        "Période analysée",
        min_value=min_y, max_value=max_y,
        value=(min_y, max_y),
        help="Filtre l'évolution annuelle et la croissance.",
    )
    mask = (launches_by_year["year"] >= y_from) & (launches_by_year["year"] <= y_to)
    lby_filtered = launches_by_year[mask]
else:
    lby_filtered = launches_by_year
    y_from = y_to = None

# =========================================================
# Vue détaillée pour KPIs filtrés par période
# Nécessite la vue SQL dev.launches_dashboard_detail
# Colonnes attendues : year, country, agency
# =========================================================
try:
    detail = load_view("launches_dashboard_detail")

    if y_from is not None and y_to is not None:
        detail_filtered = detail[
            (detail["year"] >= y_from) &
            (detail["year"] <= y_to)
        ]
    else:
        detail_filtered = detail

except Exception:
    # Fallback si la vue SQL n'existe pas encore
    detail_filtered = None


# =========================================================
# KPIs calculés dynamiquement
# - total_launches utilise déjà lby_filtered
# - pays leader / agence / pays actifs utilisent detail_filtered
# =========================================================
total_launches = int(lby_filtered["launches"].sum()) if not lby_filtered.empty else 0

if detail_filtered is not None and not detail_filtered.empty:

    # Pays leader sur la période sélectionnée
    top_country_row = (
        detail_filtered
        .dropna(subset=["country"])
        .groupby("country")
        .size()
        .reset_index(name="launches")
        .sort_values("launches", ascending=False)
        .iloc[0]
    )

    # Agence dominante sur la période sélectionnée
    top_agency_row = (
        detail_filtered
        .dropna(subset=["agency"])
        .groupby("agency")
        .size()
        .reset_index(name="launches")
        .sort_values("launches", ascending=False)
        .iloc[0]
    )

    # Nombre de pays actifs sur la période sélectionnée
    nb_countries = detail_filtered["country"].dropna().nunique()

else:
    # Fallback : anciennes vues globales si la vue détaillée n'est pas disponible
    top_country_row = (
        launches_by_country.sort_values("launches", ascending=False).iloc[0]
        if not launches_by_country.empty else None
    )

    top_agency_row = (
        top_agencies.sort_values("launches", ascending=False).iloc[0]
        if not top_agencies.empty else None
    )

    nb_countries = (
        launches_by_country["country"].nunique()
        if not launches_by_country.empty else 0
    )

c1, c2, c3, c4 = st.columns(4)
with c1:
    kpi_card("Lancements (période)", f"{total_launches:,}".replace(",", " "))
with c2:
    kpi_card(
        "Pays leader",
        top_country_row["country"] if top_country_row is not None else "—",
        delta=f"{int(top_country_row['launches'])} lancements" if top_country_row is not None else "",
    )
with c3:
    kpi_card(
        "Agence dominante",
        top_agency_row["agency"] if top_agency_row is not None else "—",
        delta=f"{int(top_agency_row['launches'])} lancements" if top_agency_row is not None else "",
    )
with c4:
    kpi_card("Pays actifs", f"{nb_countries}")

st.markdown("")
st.divider()

# ----- Évolution annuelle -----
st.subheader("Évolution annuelle des lancements")
chart_years = lby_filtered.sort_values("year")
missing_years = []

if not chart_years.empty:
    full_years = pd.DataFrame(
        {"year": range(int(chart_years["year"].min()), int(chart_years["year"].max()) + 1)}
    )
    chart_years = full_years.merge(chart_years, on="year", how="left")
    missing_years = chart_years[chart_years["launches"].isna()]["year"].astype(int).tolist()

if missing_years:
    st.warning(
        "La série historique est encore incomplète: certaines années du backfill ne "
        "sont pas encore en base. Le graphique coupe volontairement les trous au lieu "
        "de tracer une tendance artificielle."
    )

fig_year = px.line(
    chart_years, x="year", y="launches",
    color_discrete_sequence=[ARTEMIS_COLORS[0]],
    markers=True,
)
fig_year.update_traces(
    line=dict(width=2.5),
    connectgaps=False,
    hovertemplate="Année %{x}<br>%{y} lancements<extra></extra>",
)
style_plotly(fig_year, height=360)
st.plotly_chart(fig_year, use_container_width=True)

if not lby_filtered.empty:
    peak = lby_filtered.loc[lby_filtered["launches"].idxmax()]
    insight(
        f"Pic d'activité atteint en <strong>{int(peak['year'])}</strong> "
        f"avec <strong>{int(peak['launches'])}</strong> lancements."
    )

# ----- Top agences + répartition pays -----
col1, col2 = st.columns(2)

with col1:
    st.subheader("Top 10 agences")
    top10 = top_agencies.head(10)
    fig_agencies = px.bar(
        top10, x="launches", y="agency", orientation="h",
        color="launches",
        color_continuous_scale=["#A5B4FC", "#6366F1", "#4338CA"],
    )
    fig_agencies.update_layout(yaxis={"categoryorder": "total ascending"})
    fig_agencies.update_coloraxes(showscale=False)
    fig_agencies.update_traces(
        marker_line_width=0,
        hovertemplate="<b>%{y}</b><br>%{x} lancements<extra></extra>",
    )
    style_plotly(fig_agencies, height=420)
    st.plotly_chart(fig_agencies, use_container_width=True)

with col2:
    st.subheader("Répartition par pays")
    top_countries = launches_by_country.sort_values("launches", ascending=False).head(8)
    fig_country = px.pie(
        top_countries, names="country", values="launches",
        color_discrete_sequence=ARTEMIS_COLORS, hole=0.5,
    )
    fig_country.update_traces(
        textposition="inside",
        textinfo="percent",
        textfont_size=12,
        insidetextfont=dict(color="#FFFFFF", size=12),
        hovertemplate="<b>%{label}</b><br>%{value} lancements<br>%{percent}<extra></extra>",
    )
    style_plotly(fig_country, height=560)
    fig_country.update_layout(
        showlegend=True,
        legend=dict(
            **plotly_legend_style(),
            orientation="v",
            yanchor="top",
            y=-0.18,
            xanchor="center",
            x=0.5,
        ),
        margin=dict(l=8, r=8, t=20, b=240),
    )   
    st.plotly_chart(fig_country, use_container_width=True)

# ----- Croissance -----
st.subheader("Croissance annuelle (%)")
growth_source = launches_by_year.sort_values("year")
growth_filtered = pd.DataFrame(columns=["year", "growth_pct"])

if not growth_source.empty:
    full_growth_years = pd.DataFrame(
        {"year": range(int(growth_source["year"].min()), int(growth_source["year"].max()) + 1)}
    )
    growth_source = full_growth_years.merge(growth_source, on="year", how="left")
    growth_source["previous_launches"] = growth_source["launches"].shift(1)
    growth_source["growth_pct"] = (
        (growth_source["launches"] - growth_source["previous_launches"])
        / growth_source["previous_launches"]
        * 100
    )

    valid_growth = (
        growth_source["launches"].notna()
        & growth_source["previous_launches"].notna()
        & (growth_source["previous_launches"] >= 10)
    )
    growth_source.loc[~valid_growth, "growth_pct"] = pd.NA

    growth_filtered = (
        growth_source[(growth_source["year"] >= y_from) & (growth_source["year"] <= y_to)]
        if y_from is not None else growth_source
    )

if growth_filtered["growth_pct"].isna().any():
    st.caption(
        "Les années sans historique continu, ou avec moins de 10 lancements l'année "
        "précédente, sont masquées pour éviter des pourcentages artificiellement énormes."
    )

fig_growth = px.bar(
    growth_filtered, x="year", y="growth_pct",
    color="growth_pct",
    color_continuous_scale=["#EF4444", "#FAFAFA", "#10B981"],
    color_continuous_midpoint=0,
)
fig_growth.update_coloraxes(showscale=False)
fig_growth.update_traces(
    marker_line_width=0,
    outsidetextfont=dict(color="#111827", size=12),
    hovertemplate="Année %{x}<br>%{y:.1f}%<extra></extra>",
)
style_plotly(fig_growth, height=320)
st.plotly_chart(fig_growth, use_container_width=True)

valid_growth_filtered = growth_filtered.dropna(subset=["growth_pct"])
if not valid_growth_filtered.empty:
    best = valid_growth_filtered.loc[valid_growth_filtered["growth_pct"].idxmax()]
    insight(
        f"Croissance maximale en <strong>{int(best['year'])}</strong>: "
        f"<strong>+{best['growth_pct']:.1f}%</strong> vs année précédente."
    )
