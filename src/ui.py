"""Composants UI partagés: thème, sidebar, protection, KPIs, insights, Plotly."""
import streamlit as st
from src.auth import logout

# Palette Artemis — cohérence visuelle entre toutes les pages
ARTEMIS_COLORS = [
    "#6366F1", "#EC4899", "#10B981", "#F59E0B",
    "#06B6D4", "#8B5CF6", "#EF4444", "#84CC16",
]
PRIMARY = "#6366F1"
ACCENT = "#EC4899"


def apply_theme() -> None:
    """Injecte le CSS global de l'application (appelé une fois dans app.py)."""
    st.markdown(
        """
        <style>
        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        h1 { font-weight: 700 !important; letter-spacing: -0.02em; }
        h2, h3 { font-weight: 600 !important; letter-spacing: -0.01em; }

        /* Cartes KPI */
        .artemis-kpi {
            background: linear-gradient(135deg, rgba(99,102,241,0.06), rgba(236,72,153,0.06));
            border: 1px solid rgba(99,102,241,0.15);
            border-radius: 14px;
            padding: 1.1rem 1.25rem;
            height: 100%;
        }
        .artemis-kpi .label {
            font-size: 0.78rem; font-weight: 500; color: #6b7280;
            text-transform: uppercase; letter-spacing: 0.05em; margin: 0;
        }
        .artemis-kpi .value {
            font-size: 1.85rem; font-weight: 700; color: #111827;
            margin: 0.25rem 0 0 0; line-height: 1.1;
        }
        .artemis-kpi .delta {
            font-size: 0.85rem; color: #10B981;
            font-weight: 500; margin-top: 0.35rem;
        }
        .artemis-kpi .delta.neg { color: #EF4444; }

        /* Encart insight automatique */
        .artemis-insight {
            background: linear-gradient(135deg, rgba(16,185,129,0.08), rgba(6,182,212,0.08));
            border-left: 4px solid #10B981;
            border-radius: 8px;
            padding: 0.85rem 1.1rem;
            margin: 0.6rem 0;
            color: #064e3b;
            font-size: 0.95rem;
        }
        .artemis-insight strong { color: #047857; }

        /* En-tête de page */
        .artemis-header {
            margin-bottom: 1rem;
            padding-bottom: 0.75rem;
            border-bottom: 1px solid rgba(0,0,0,0.06);
        }
        .artemis-header .eyebrow {
            color: #6366F1; font-size: 0.8rem; font-weight: 600;
            text-transform: uppercase; letter-spacing: 0.08em;
        }
        .artemis-header h1 { margin: 0.15rem 0 0.35rem 0; font-size: 2rem; }
        .artemis-header p { color: #6b7280; margin: 0; font-size: 1rem; }

        /* Hero page connexion */
        .artemis-hero { text-align: center; padding: 2.2rem 1rem 1.4rem 1rem; }
        .artemis-hero .badge {
            display: inline-block;
            background: rgba(99,102,241,0.1);
            color: #6366F1;
            padding: 0.25rem 0.75rem;
            border-radius: 999px;
            font-size: 0.78rem; font-weight: 600; letter-spacing: 0.04em;
        }
        .artemis-hero h1 {
            font-size: 2.5rem; margin: 0.6rem 0 0.4rem 0;
            background: linear-gradient(135deg, #6366F1, #EC4899);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .artemis-hero p { color: #6b7280; font-size: 1.05rem; }

        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #ffffff 0%, #f9fafb 100%);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def require_auth():
    """Garde d'authentification. À appeler en tête de chaque page privée."""
    user = st.session_state.get("user")
    if user is None:
        st.warning("Session expirée. Veuillez vous reconnecter.")
        st.stop()
    return user


def render_sidebar(user) -> None:
    """Sidebar partagée: identité utilisateur + déconnexion + footer."""
    with st.sidebar:
        st.markdown(
            f"""
            <div style="padding: 0.85rem 0.5rem; border-radius: 10px;
                 background: rgba(99,102,241,0.06); margin-bottom: 0.5rem;">
              <div style="font-size: 0.72rem; color: #6b7280;
                   text-transform: uppercase; letter-spacing: 0.05em;">
                Compte actif
              </div>
              <div style="font-weight: 600; color: #111827; margin-top: 0.15rem;
                   font-size: 0.92rem; word-break: break-all;">
                {user.email}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("🚪 Se déconnecter", use_container_width=True):
            logout()
            st.rerun()
        st.caption("Artemis · v1.1 · © 2026")


def page_header(title: str, subtitle: str = "", eyebrow: str = "") -> None:
    """En-tête de page cohérent (eyebrow + titre + sous-titre)."""
    eyebrow_html = f'<div class="eyebrow">{eyebrow}</div>' if eyebrow else ""
    subtitle_html = f"<p>{subtitle}</p>" if subtitle else ""
    st.markdown(
        f"""
        <div class="artemis-header">
          {eyebrow_html}
          <h1>{title}</h1>
          {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi_card(label: str, value, delta: str = "", positive: bool = True) -> None:
    """Carte KPI stylisée (à placer dans un st.columns)."""
    delta_html = ""
    if delta:
        cls = "delta" if positive else "delta neg"
        delta_html = f'<div class="{cls}">{delta}</div>'
    st.markdown(
        f"""
        <div class="artemis-kpi">
          <p class="label">{label}</p>
          <p class="value">{value}</p>
          {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def insight(text: str) -> None:
    """Encart insight automatique (texte HTML autorisé)."""
    st.markdown(
        f'<div class="artemis-insight">💡 <strong>Insight</strong> · {text}</div>',
        unsafe_allow_html=True,
    )


def style_plotly(fig, height: int = 400):
    """Applique le template Artemis à une figure Plotly."""
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=10, r=10, t=40, b=10),
        font=dict(family="Inter, sans-serif", size=12, color="#374151"),
        legend=dict(
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="rgba(0,0,0,0.05)",
            borderwidth=1,
        ),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig