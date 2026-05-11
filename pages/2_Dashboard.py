import streamlit as st
import plotly.express as px
from src.queries import load_dashboard_data

st.set_page_config(
    page_title="Dashboard Artemis",
    page_icon="🚀",
    layout="wide"
)

if "user" not in st.session_state:
    st.warning("Veuillez vous connecter pour accéder au dashboard.")
    st.stop()

user = st.session_state["user"]

st.sidebar.success(f"Connecté : {user.email}")

if st.sidebar.button("Déconnexion"):
    del st.session_state["user"]
    st.switch_page("pages/1_Connexion.py")

st.title("🚀 Dashboard des Lancements Spatiaux")
st.caption(f"Bienvenue {user.email}")

data = load_dashboard_data()

launches_by_year = data["launches_by_year"]
top_agencies = data["top_agencies"]
launches_by_country = data["launches_by_country"]
growth = data["growth"]

col1, col2, col3 = st.columns(3)

col1.metric("Total lancements", "220")
col2.metric("Pays dominant", "USA")
col3.metric("Agence dominante", "US Air Force")

st.divider()

st.subheader("📈 Évolution des lancements par année")

fig_year = px.line(
    launches_by_year,
    x="year",
    y="launches",
    markers=True,
    title="Nombre de lancements par année"
)

st.plotly_chart(fig_year, use_container_width=True)

col1, col2 = st.columns(2)

with col1:
    st.subheader("🏢 Top agences spatiales")

    fig_agencies = px.bar(
        top_agencies.head(10),
        x="launches",
        y="agency",
        orientation="h",
        title="Agences les plus actives"
    )

    fig_agencies.update_layout(
        yaxis={"categoryorder": "total ascending"}
    )

    st.plotly_chart(fig_agencies, use_container_width=True)

with col2:
    st.subheader("🌍 Répartition par pays")

    fig_country = px.pie(
        launches_by_country,
        names="country",
        values="launches",
        title="Répartition géographique"
    )

    st.plotly_chart(fig_country, use_container_width=True)

st.subheader("📊 Croissance annuelle des lancements")

fig_growth = px.bar(
    growth,
    x="year",
    y="growth_pct",
    title="Croissance annuelle (%)"
)

st.plotly_chart(fig_growth, use_container_width=True)

st.info(
    "Insight : les lancements spatiaux connaissent une forte croissance entre 1957 et 1961, "
    "dans un contexte de course à l’espace dominé par les États-Unis et l’Union soviétique."
)