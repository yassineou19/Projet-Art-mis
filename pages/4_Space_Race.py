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
    "🏁 Space Race"
)

st.caption(
    "Comparaison des agences spatiales."
)

df = load_data(
    "select * from space_race_agencies"
)

top_n = st.slider(
    "Nombre d'agences",
    5,
    20,
    10
)

df_top = df.head(top_n)

# KPIs
col1, col2, col3 = st.columns(3)

col1.metric(
    "Agence dominante",
    df.iloc[0]["agency"]
)

col2.metric(
    "Lancements",
    int(df.iloc[0]["launches"])
)

col3.metric(
    "Part activité",
    f"{df.iloc[0]['market_share_pct']}%"
)

st.divider()

# BAR CHART
fig_bar = px.bar(
    df_top,
    x="launches",
    y="agency",
    orientation="h",
    color="agency"
)

fig_bar.update_layout(
    yaxis={
        "categoryorder":
        "total ascending"
    }
)

st.plotly_chart(
    fig_bar,
    use_container_width=True
)

# SCATTER
fig_scatter = px.scatter(
    df_top,
    x="active_years",
    y="launches",
    size="market_share_pct",
    color="agency",
    hover_name="agency"
)

st.plotly_chart(
    fig_scatter,
    use_container_width=True
)

# PIE
fig_pie = px.pie(
    df_top,
    names="agency",
    values="market_share_pct"
)

st.plotly_chart(
    fig_pie,
    use_container_width=True
)