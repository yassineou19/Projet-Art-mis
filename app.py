import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px

st.set_page_config(
    page_title="Dashboard Lancements Spatiaux",
    layout="wide"
)

st.title("🚀 Analyse des Lancements Spatiaux")

# Connexion Supabase PostgreSQL
conn = psycopg2.connect(
    host="aws-1-eu-central-1.pooler.supabase.com",
    database="postgres",
    user="postgres.olcuybolhpccnncaupts",
    password="tfxYLOIBeLO6NTuB",
    port="5432"
)

# Chargement des vues
launches_by_year = pd.read_sql("select * from launches_by_year", conn)
top_agencies = pd.read_sql("select * from top_agencies", conn)
launches_by_country = pd.read_sql("select * from launches_by_country", conn)
growth = pd.read_sql("select * from launches_growth_by_year", conn)

# KPIs
col1, col2, col3 = st.columns(3)

col1.metric("Total lancements", "220")
col2.metric("Pays dominant", "USA")
col3.metric("Agence dominante", "US Air Force")

# Graphique évolution
st.subheader("Évolution des lancements par année")
fig_year = px.line(
    launches_by_year,
    x="year",
    y="launches",
    markers=True
)
st.plotly_chart(fig_year, use_container_width=True)

# Graphiques en colonnes
col1, col2 = st.columns(2)

with col1:
    st.subheader("Top agences")
    fig_agencies = px.bar(
        top_agencies,
        x="launches",
        y="agency",
        orientation="h"
    )
    st.plotly_chart(fig_agencies, use_container_width=True)

with col2:
    st.subheader("Répartition par pays")
    fig_country = px.pie(
        launches_by_country,
        names="country",
        values="launches"
    )
    st.plotly_chart(fig_country, use_container_width=True)

# Croissance
st.subheader("Croissance annuelle des lancements (%)")
fig_growth = px.bar(
    growth,
    x="year",
    y="growth_pct"
)
st.plotly_chart(fig_growth, use_container_width=True)

st.info(
    "Insight : les lancements spatiaux connaissent une forte croissance entre 1957 et 1961, "
    "dans un contexte de course à l’espace dominé par les États-Unis et l’Union soviétique."
)