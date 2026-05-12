"""Space Race — comparaison des agences, KPIs de domination, lecture analyste."""
import streamlit as st
import plotly.express as px
from src.queries import load_view
from src.ui import (
    require_auth, render_sidebar, page_header,
    kpi_card, insight, style_plotly, ARTEMIS_COLORS,
)

user = require_auth()
render_sidebar(user)

page_header(
    title="Space Race · concurrence des agences",
    subtitle="Quelle agence domine? Sur combien d'années? Avec quelle part d'activité?",
    eyebrow="ANALYTICS · COMPETITION",
)

try:
    df = load_view("space_race_agencies")
except Exception as e:
    st.error(f"Impossible de charger les données: {e}")
    st.stop()

if df.empty:
    st.warning("Aucune donnée disponible.")
    st.stop()

df = df.sort_values("launches", ascending=False).reset_index(drop=True)

top_n = st.slider("Nombre d'agences comparées", 5, min(25, len(df)), 10)
df_top = df.head(top_n)

# KPIs domination
leader = df.iloc[0]
runner_up = df.iloc[1] if len(df) > 1 else None
gap = (leader["launches"] - runner_up["launches"]) if runner_up is not None else 0
total_market = df["launches"].sum()
leader_share = (leader["launches"] / total_market * 100) if total_market else 0

c1, c2, c3, c4 = st.columns(4)
with c1:
    kpi_card("Leader", leader["agency"])
with c2:
    kpi_card("Lancements leader", f"{int(leader['launches']):,}".replace(",", " "))
with c3:
    kpi_card("Part de marché", f"{leader_share:.1f}%")
with c4:
    kpi_card(
        "Écart vs #2",
        f"+{int(gap)}" if runner_up is not None else "—",
        delta=runner_up["agency"] if runner_up is not None else "",
    )

st.markdown("")
st.divider()

# Bar chart
st.subheader("🏢 Volume d'activité par agence")
fig_bar = px.bar(
    df_top, x="launches", y="agency", orientation="h",
    color="agency", color_discrete_sequence=ARTEMIS_COLORS,
    text="launches",
)
fig_bar.update_layout(yaxis={"categoryorder": "total ascending"}, showlegend=False)
fig_bar.update_traces(
    textposition="outside",
    marker_line_width=0,
    cliponaxis=False,
    outsidetextfont=dict(color="#111827", size=12),
    hovertemplate="<b>%{y}</b><br>%{x} lancements<extra></extra>",
)
style_plotly(fig_bar, height=480)
fig_bar.update_layout(margin=dict(l=20, r=70, t=34, b=34))
st.plotly_chart(fig_bar, use_container_width=True)

# Scatter + pie
col1, col2 = st.columns([3, 2])

with col1:
    st.subheader("⏱️ Longévité vs activité")
    fig_scatter = px.scatter(
        df_top,
        x="active_years", y="launches",
        size="market_share_pct",
        color="agency", color_discrete_sequence=ARTEMIS_COLORS,
        hover_name="agency", size_max=55,
        labels={
            "active_years": "Années d'activité",
            "launches": "Lancements",
            "market_share_pct": "Part (%)",
        },
    )
    fig_scatter.update_traces(
        marker=dict(line=dict(width=0), opacity=0.82),
        hovertemplate=(
            "<b>%{hovertext}</b><br>"
            "Années actives: %{x}<br>"
            "Lancements: %{y}<br>"
            "<extra></extra>"
        )
    )
    style_plotly(fig_scatter, height=460)
    st.plotly_chart(fig_scatter, use_container_width=True)

with col2:
    st.subheader("🥧 Parts d'activité")
    fig_pie = px.pie(
        df_top, names="agency", values="market_share_pct",
        hole=0.55, color_discrete_sequence=ARTEMIS_COLORS,
    )
    fig_pie.update_traces(
        textposition="inside",
        textinfo="percent",
        textfont_size=12,
        insidetextfont=dict(color="#FFFFFF", size=12),
        hovertemplate="<b>%{label}</b><br>Part: %{value:.1f}%<extra></extra>",
    )
    style_plotly(fig_pie, height=460)
    fig_pie.update_layout(
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.05,
            xanchor="center",
            x=0.5,
            font=dict(size=10, color="#111827"),
        ),
        margin=dict(l=8, r=8, t=20, b=110),
    )
    st.plotly_chart(fig_pie, use_container_width=True)

# Insight
top3_share = df.head(3)["market_share_pct"].sum()
insight(
    f"Concentration: les <strong>3 premières agences</strong> représentent "
    f"<strong>{top3_share:.1f}%</strong> du marché — historiquement oligopolistique, "
    f"mais en redéfinition rapide avec les nouveaux entrants privés."
)

with st.expander("📑 Lecture analyste / investisseur"):
    st.markdown(
        """
        - **Volume d'activité** (bar chart) → mesure la *capacité opérationnelle* cumulée.
        - **Longévité × activité** (scatter) → distingue les *acteurs historiques durables*
          (forte longévité, fort volume) des *nouveaux entrants intenses*
          (faible longévité, fort volume — souvent privés).
        - **Parts d'activité** (donut) → degré de concentration du marché.
          Une part >40% pour un seul acteur signale un quasi-monopole sur la période.
        """
    )
