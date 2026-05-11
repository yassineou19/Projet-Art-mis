"""Carte mondiale — slider période, projection, KPIs, insight."""
import streamlit as st
import plotly.express as px
from src.queries import load_view
from src.ui import (
    require_auth, render_sidebar, page_header,
    kpi_card, insight, style_plotly,
)

user = require_auth()
render_sidebar(user)

page_header(
    title="Carte mondiale des lancements",
    subtitle="Géographie des sites actifs: identifier les hubs et l'émergence de nouveaux acteurs.",
    eyebrow="ANALYTICS · GEOGRAPHY",
)

try:
    df = load_view("launches_map")
except Exception as e:
    st.error(f"Impossible de charger les données: {e}")
    st.stop()

years = sorted(df["launch_year"].dropna().unique().astype(int).tolist())
if not years:
    st.warning("Aucune donnée géographique disponible.")
    st.stop()

# Contrôles
ctrl1, ctrl2 = st.columns([3, 1])
with ctrl1:
    y_min, y_max = min(years), max(years)
    y_from, y_to = st.slider(
        "Période",
        min_value=y_min, max_value=y_max,
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

# Agrégation par site
country_counts = (
    filtered
    .groupby(["country", "latitude", "longitude"])
    .size()
    .reset_index(name="launches")
    .sort_values("launches", ascending=False)
)

# KPIs
k1, k2, k3 = st.columns(3)
with k1:
    kpi_card("Lancements affichés", f"{int(country_counts['launches'].sum())}")
with k2:
    kpi_card("Sites actifs", f"{len(country_counts)}")
with k3:
    top_site = country_counts.iloc[0]
    kpi_card(
        "Site #1",
        top_site["country"],
        delta=f"{int(top_site['launches'])} lancements",
    )

st.markdown("")

# Carte
fig = px.scatter_geo(
    country_counts,
    lat="latitude", lon="longitude",
    size="launches", size_max=42,
    color="country",
    hover_name="country",
    hover_data={"launches": True, "latitude": ":.2f", "longitude": ":.2f"},
    projection=projection,
)
fig.update_geos(
    showcountries=True, countrycolor="rgba(0,0,0,0.15)",
    showland=True, landcolor="#f9fafb",
    showocean=True, oceancolor="#eff6ff",
)
fig.update_layout(height=620, showlegend=False)
style_plotly(fig, height=620)
st.plotly_chart(fig, use_container_width=True)

# Insight auto
top3 = country_counts.head(3)
parts = ", ".join(
    f"<strong>{r['country']}</strong> ({int(r['launches'])})"
    for _, r in top3.iterrows()
)
insight(
    f"Sur la période <strong>{y_from}–{y_to}</strong>, le top 3 des sites cumule "
    f"{int(top3['launches'].sum())} lancements ({parts})."
)

with st.expander("ℹ️ Lecture business"):
    st.markdown(
        """
        Cette carte met en évidence la **concentration géographique** de l'activité spatiale.
        Quelques sites historiques (Baïkonour, Cape Canaveral, Plesetsk, Jiuquan…) dominent
        encore le volume, mais l'émergence de nouveaux sites — notamment privés —
        redessine la carte sur les périodes récentes.

        💡 *Astuce*: comparer **avant / après 2010** met en évidence l'essor de SpaceX et de la Chine.
        """
    )