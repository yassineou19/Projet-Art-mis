import streamlit as st
import plotly.express as px
from src.queries import load_data

# PROTECTION
if "user" not in st.session_state:
    st.warning("Veuillez vous connecter.")
    st.stop()

st.set_page_config(
    page_title="Carte Mondiale",
    page_icon="🌍",
    layout="wide"
)

st.title("🌍 Activité Spatiale Mondiale")

st.caption(
    "Visualisation des activités spatiales par pays."
)

# LOAD DATA
df = load_data("select * from launches_map")

# FILTRE ANNÉE
years = sorted(df["launch_year"].dropna().unique())

selected_year = st.selectbox(
    "Choisir une année",
    years
)

filtered_df = df[df["launch_year"] == selected_year]

# MAP
fig = px.scatter_geo(
    filtered_df,
    lat="latitude",
    lon="longitude",
    hover_name="country",
    size_max=30,
    projection="natural earth",
    color="country"
)

fig.update_layout(
    height=700,
    margin=dict(l=0, r=0, t=50, b=0)
)

st.plotly_chart(fig, use_container_width=True)

# INSIGHT
st.info(
    f"Analyse {selected_year} : "
    "les États-Unis dominent l’activité spatiale mondiale."
)