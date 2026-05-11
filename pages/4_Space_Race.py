import streamlit as st
import plotly.express as px
from src.queries import load_data

st.set_page_config(
    page_title="Space Race",
    page_icon="🏁",
    layout="wide"
)

if "user" not in st.session_state:
    st.warning("Veuillez vous connecter pour accéder à cette page.")
    st.stop()

st.title("🏁 Space Race — Comparaison des acteurs spatiaux")
st.caption("Analyse comparative des agences selon leur volume, leur ancienneté et leur part d’activité.")

df = load_data("select * from space_race_agencies")

top_n = st.slider("Nombre d'agences à comparer", 5, 20, 10)
df_top = df.head(top_n)

col1, col2, col3 = st.columns(3)

col1.metric("Agence dominante", df.iloc[0]["agency"])
col2.metric("Total lancements top agence", int(df.iloc[0]["launches"]))
col3.metric("Part d’activité top agence", f"{df.iloc[0]['market_share_pct']}%")

st.divider()

col1, col2 = st.columns(2)

with col1:
    fig = px.bar(
        df_top,
        x="launches",
        y="agency",
        orientation="h",
        title=f"Top {top_n} agences par nombre de lancements"
    )
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig, use_container_width=True)

with col2:
    fig = px.scatter(
        df_top,
        x="active_years",
        y="launches",
        size="market_share_pct",
        color="agency",
        hover_name="agency",
        title="Volume vs ancienneté d’activité"
    )
    st.plotly_chart(fig, use_container_width=True)

st.subheader("📊 Part d’activité par agence")

fig_share = px.pie(
    df_top,
    names="agency",
    values="market_share_pct",
    title=f"Part d’activité des {top_n} principales agences"
)

st.plotly_chart(fig_share, use_container_width=True)

leader = df.iloc[0]

st.info(
    f"Insight : {leader['agency']} domine la période analysée avec "
    f"{int(leader['launches'])} lancements, soit {leader['market_share_pct']}% de l’activité totale."
)