import streamlit as st
import plotly.express as px
from src.queries import load_data

# PROTECTION
if st.session_state["user"] is None:
    st.rerun()

user = st.session_state["user"]

# SIDEBAR
with st.sidebar:

    st.success(
        f"Connecté : {user.email}"
    )

    if st.button(
        "🚪 Se déconnecter",
        use_container_width=True
    ):

        st.session_state["user"] = None

        st.rerun()

# PAGE
st.title(
    "🌍 Carte Mondiale des Lancements"
)

df = load_data(
    "select * from launches_map"
)

years = sorted(
    df["launch_year"]
    .dropna()
    .unique()
)

selected_year = st.selectbox(
    "Choisir une année",
    years
)

filtered_df = df[
    df["launch_year"]
    == selected_year
]

country_counts = (
    filtered_df
    .groupby(
        [
            "country",
            "latitude",
            "longitude"
        ]
    )
    .size()
    .reset_index(
        name="launches"
    )
)

fig = px.scatter_geo(
    country_counts,
    lat="latitude",
    lon="longitude",
    size="launches",
    color="country",
    hover_name="country",
    projection="natural earth"
)

fig.update_layout(
    height=700
)

st.plotly_chart(
    fig,
    use_container_width=True
)