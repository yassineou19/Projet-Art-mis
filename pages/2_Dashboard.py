import streamlit as st
import plotly.express as px
from src.queries import load_dashboard_data

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
    "📊 Dashboard des Lancements Spatiaux"
)

st.caption(
    f"Bienvenue {user.email}"
)

# DATA
data = load_dashboard_data()

launches_by_year = data["launches_by_year"]

top_agencies = data["top_agencies"]

launches_by_country = data["launches_by_country"]

growth = data["growth"]

# KPIs
col1, col2, col3 = st.columns(3)

col1.metric(
    "Total lancements",
    "220"
)

col2.metric(
    "Pays dominant",
    "USA"
)

col3.metric(
    "Agence dominante",
    "US Air Force"
)

st.divider()

# EVOLUTION
st.subheader(
    "📈 Évolution des lancements par année"
)

fig_year = px.line(
    launches_by_year,
    x="year",
    y="launches",
    markers=True
)

st.plotly_chart(
    fig_year,
    use_container_width=True
)

# GRAPHIQUES
col1, col2 = st.columns(2)

with col1:

    st.subheader(
        "🏢 Top agences spatiales"
    )

    fig_agencies = px.bar(
        top_agencies.head(10),
        x="launches",
        y="agency",
        orientation="h"
    )

    fig_agencies.update_layout(
        yaxis={
            "categoryorder":
            "total ascending"
        }
    )

    st.plotly_chart(
        fig_agencies,
        use_container_width=True
    )

with col2:

    st.subheader(
        "🌍 Répartition par pays"
    )

    fig_country = px.pie(
        launches_by_country,
        names="country",
        values="launches"
    )

    st.plotly_chart(
        fig_country,
        use_container_width=True
    )

# CROISSANCE
st.subheader(
    "📊 Croissance annuelle"
)

fig_growth = px.bar(
    growth,
    x="year",
    y="growth_pct"
)

st.plotly_chart(
    fig_growth,
    use_container_width=True
)

st.info(
    "Insight : forte croissance des lancements "
    "entre 1957 et 1961."
)