"""Carte mondiale — projection, période, KPIs, insight."""

import streamlit as st
import plotly.express as px

from src.queries import load_view
from src.ui import (
    require_auth, render_sidebar, page_header, kpi_card,
    insight, style_plotly, section_title, format_number,
    get_theme_mode,
)

user = require_auth()
render_sidebar(user)

page_header(
    title="Carte mondiale des lancements",
    subtitle="Géographie des sites actifs : identifier les hubs et l'émergence de nouveaux acteurs.",
    eyebrow="ANALYTICS · GEOGRAPHY",
    badge="Géospatial",
)

try:
    df = load_view("launches_map")
except Exception as e:
    st.error(f"Impossible de charger les données : {e}")
    st.stop()

years = sorted(df["launch_year"].dropna().unique().astype(int).tolist())
if not years:
    st.warning("Aucune donnée géographique disponible.")
    st.stop()

# === Filtres ===
ctrl1, ctrl2 = st.columns([3, 1])
with ctrl1:
    y_min, y_max = min(years), max(years)
    y_from, y_to = st.slider(
        "Période", min_value=y_min, max_value=y_max,
        value=(y_min, y_max),
        help="Filtre les lancements affichés sur la carte.",
    )
with ctrl2:
    projection = st.selectbox(
        "Projection",
        ["natural earth", "orthographic", "equirectangular"],
        index=0,
    )

mask = (df["launch_year"] >= y_from) & (df["launch_year"] <= y_to)
filtered = df[mask]

if filtered.empty:
    st.warning("Aucun lancement sur la période sélectionnée.")
    st.stop()

country_counts = (
    filtered.groupby(["country", "latitude", "longitude"])
    .size().reset_index(name="launches")
    .sort_values("launches", ascending=False)
)

# === KPIs ===
k1, k2, k3 = st.columns(3)
with k1:
    kpi_card("Lancements affichés", format_number(int(country_counts["launches"].sum())))
with k2:
    kpi_card("Sites actifs", str(len(country_counts)))
with k3:
    top_site = country_counts.iloc[0]
    kpi_card(
        "Site #1",
        str(top_site["country"]),
        delta=f"{format_number(top_site['launches'])} lancements",
    )

st.markdown("")

# === Carte ===
section_title("Carte des sites actifs")

mode = get_theme_mode()

fig = px.scatter_geo(
    country_counts,
    lat="latitude", lon="longitude",
    size="launches", size_max=42,
    color="country", hover_name="country",
    hover_data={"launches": True, "latitude": ":.2f", "longitude": ":.2f"},
    projection=projection,
)

if mode == "dark":
    fig.update_geos(
        bgcolor="rgba(0,0,0,0)",
        showcountries=True, countrycolor="rgba(255,255,255,0.12)",
        showland=True, landcolor="#0B1020",
        showocean=True, oceancolor="#050816",
        showcoastlines=True, coastlinecolor="rgba(255,255,255,0.18)",
        showlakes=True, lakecolor="#050816",
        framecolor="rgba(255,255,255,0.10)",
    )
else:
    fig.update_geos(
        bgcolor="rgba(0,0,0,0)",
        showcountries=True, countrycolor="rgba(15,23,42,0.18)",
        showland=True, landcolor="#F1F5F9",
        showocean=True, oceancolor="#EEF2FF",
        showcoastlines=True, coastlinecolor="rgba(15,23,42,0.20)",
        showlakes=True, lakecolor="#EEF2FF",
    )

fig.update_layout(height=620, showlegend=False)
style_plotly(fig, height=620)
st.plotly_chart(fig, use_container_width=True)

# === Insight ===
top3 = country_counts.head(3)
parts = ", ".join(
    f"<strong>{r['country']}</strong> ({int(r['launches'])})"
    for _, r in top3.iterrows()
)
insight(
    f"Sur la période <strong>{y_from}–{y_to}</strong>, le top 3 cumule "
    f"<strong>{int(top3['launches'].sum())}</strong> lancements ({parts})."
)

with st.expander("ℹ️ Lecture business"):
    st.markdown(
        """
        Cette carte met en évidence la **concentration géographique** de l'activité spatiale.
        Quelques sites historiques dominent encore le volume, mais l'émergence de nouveaux sites,
        notamment privés, redessine la carte sur les périodes récentes.

        💡 *Astuce* : comparer **avant / après 2010** met en évidence l'essor de SpaceX et de la Chine.
        """
    )