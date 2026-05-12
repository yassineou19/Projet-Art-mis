"""Artemis — Design system (thèmes, composants, sidebar, Plotly)."""

from __future__ import annotations

import os
import streamlit as st

from src.auth import logout


# =========================================================
# THEMES
# =========================================================

THEMES: dict[str, dict[str, str]] = {
    "dark": {
        "bg": "#050816",
        "bg_secondary": "#0B1020",
        "card": "#111827",
        "card_soft": "#101827",
        "text": "#F8FAFC",
        "muted": "#94A3B8",
        "muted_2": "#64748B",
        "border": "rgba(255,255,255,0.08)",
        "primary": "#7C3AED",
        "blue": "#2563EB",
        "cyan": "#06B6D4",
        "success": "#10B981",
        "warning": "#F59E0B",
        "danger": "#EF4444",
        "glass_bg": "rgba(17, 24, 39, 0.55)",
        "glass_border": "rgba(255,255,255,0.10)",
        "grid": "rgba(255,255,255,0.06)",
    },
    "light": {
        "bg": "#F8FAFC",
        "bg_secondary": "#EEF2FF",
        "card": "#FFFFFF",
        "card_soft": "#F1F5F9",
        "text": "#0F172A",
        "muted": "#64748B",
        "muted_2": "#94A3B8",
        "border": "rgba(15,23,42,0.08)",
        "primary": "#7C3AED",
        "blue": "#2563EB",
        "cyan": "#06B6D4",
        "success": "#10B981",
        "warning": "#F59E0B",
        "danger": "#EF4444",
        "glass_bg": "rgba(255, 255, 255, 0.75)",
        "glass_border": "rgba(15, 23, 42, 0.08)",
        "grid": "rgba(15,23,42,0.06)",
    },
}

ARTEMIS_COLORS = [
    "#7C3AED", "#06B6D4", "#10B981", "#F59E0B",
    "#2563EB", "#EC4899", "#EF4444", "#84CC16",
]


# =========================================================
# THEME HELPERS
# =========================================================

def get_theme_mode() -> str:
    return st.session_state.get("theme_mode", "dark")


def get_theme() -> dict:
    return THEMES[get_theme_mode()]


# =========================================================
# AUTH
# =========================================================

def get_user_email(user) -> str:
    if user is None:
        return "—"
    email = getattr(user, "email", None)
    if email:
        return email
    if isinstance(user, dict):
        return user.get("email", "—")
    return "—"


def is_admin(user) -> bool:
    if user is None:
        return False
    admin_emails = os.getenv("ADMIN_EMAILS", "")
    allowed = [e.strip().lower() for e in admin_emails.split(",") if e.strip()]
    return get_user_email(user).lower() in allowed


def require_auth():
    user = st.session_state.get("user")
    if user is None:
        st.warning("Session expirée. Veuillez vous reconnecter.")
        st.stop()
    return user


def require_admin(user) -> None:
    if not is_admin(user):
        st.error("Accès réservé aux administrateurs.")
        st.stop()


# =========================================================
# FORMATTERS
# =========================================================

def format_number(n) -> str:
    if n is None:
        return "—"
    try:
        return f"{int(n):,}".replace(",", " ")
    except (ValueError, TypeError):
        return str(n)


# =========================================================
# THEME / CSS
# =========================================================

def apply_theme(mode: str = "dark") -> None:
    """Injecte le design system Artemis avec variables CSS thème-aware."""
    if mode not in THEMES:
        mode = "dark"
    t = THEMES[mode]

    css = f"""
    <style>
    :root {{
        --bg: {t['bg']};
        --bg-secondary: {t['bg_secondary']};
        --card: {t['card']};
        --card-soft: {t['card_soft']};
        --text: {t['text']};
        --muted: {t['muted']};
        --muted-2: {t['muted_2']};
        --border: {t['border']};
        --primary: {t['primary']};
        --blue: {t['blue']};
        --cyan: {t['cyan']};
        --success: {t['success']};
        --warning: {t['warning']};
        --danger: {t['danger']};
        --glass-bg: {t['glass_bg']};
        --glass-border: {t['glass_border']};
        --grid: {t['grid']};
    }}

    /* === Background app === */
    [data-testid="stAppViewContainer"] {{
        background: var(--bg);
        background-image:
            radial-gradient(circle at 12% 8%, rgba(124,58,237,0.10), transparent 40%),
            radial-gradient(circle at 88% 92%, rgba(6,182,212,0.08), transparent 45%);
        color: var(--text);
    }}
    [data-testid="stHeader"] {{ background: transparent; }}
    .main .block-container {{
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 1400px;
    }}

    /* === Sidebar === */
    [data-testid="stSidebar"],
    [data-testid="stSidebar"] > div {{
        background: var(--bg-secondary);
        border-right: 1px solid var(--border);
    }}
    [data-testid="stSidebarNav"] a {{
        color: var(--text) !important;
    }}

    /* === Typography === */
    html, body, [class*="css"], [data-testid="stMarkdownContainer"] {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        color: var(--text);
    }}
    h1, h2, h3, h4 {{ color: var(--text) !important; font-weight: 600 !important; letter-spacing: -0.01em; }}
    h1 {{ font-weight: 700 !important; letter-spacing: -0.02em; }}
    p, label, span {{ color: var(--text); }}

    /* === Inputs === */
    .stTextInput input, .stNumberInput input, .stTextArea textarea, .stDateInput input,
    .stSelectbox div[data-baseweb="select"] > div {{
        background: var(--card) !important;
        color: var(--text) !important;
        border: 1px solid var(--border) !important;
        border-radius: 10px !important;
    }}
    .stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {{
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 3px rgba(124,58,237,0.18) !important;
    }}

    /* === Buttons === */
    .stButton > button, .stFormSubmitButton > button {{
        background: linear-gradient(135deg, var(--primary), var(--blue));
        color: #fff !important;
        border: none;
        border-radius: 10px;
        padding: 0.55rem 1.2rem;
        font-weight: 600;
        transition: transform .15s ease, box-shadow .15s ease;
        box-shadow: 0 6px 18px rgba(124,58,237,0.25);
    }}
    .stButton > button:hover, .stFormSubmitButton > button:hover {{
        transform: translateY(-1px);
        box-shadow: 0 10px 24px rgba(124,58,237,0.35);
    }}
    .stButton > button[kind="secondary"] {{
        background: var(--card);
        color: var(--text) !important;
        border: 1px solid var(--border);
        box-shadow: none;
    }}

    /* === Tabs === */
    .stTabs [data-baseweb="tab-list"] {{ gap: .4rem; border-bottom: 1px solid var(--border); }}
    .stTabs [data-baseweb="tab"] {{
        background: transparent; color: var(--muted);
        font-weight: 500; padding: .55rem .9rem;
        border-radius: 8px 8px 0 0;
    }}
    .stTabs [aria-selected="true"] {{
        color: var(--text) !important;
        border-bottom: 2px solid var(--primary) !important;
    }}

    /* === Slider / Radio === */
    .stSlider [data-baseweb="slider"] div[role="slider"] {{
        background: var(--primary); border: 2px solid #fff;
    }}
    .stRadio label, .stCheckbox label {{ color: var(--text) !important; }}

    /* === Expander === */
    [data-testid="stExpander"] {{
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 12px;
    }}

    /* === Dataframe === */
    [data-testid="stDataFrame"] {{
        background: var(--card);
        border-radius: 12px;
        border: 1px solid var(--border);
        overflow: hidden;
    }}

    /* === Divider / Alerts === */
    hr {{ border-color: var(--border) !important; }}
    [data-testid="stAlert"] {{
        background: var(--card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 12px;
        color: var(--text) !important;
    }}

    /* === Scrollbars === */
    ::-webkit-scrollbar {{ width: 10px; height: 10px; }}
    ::-webkit-scrollbar-track {{ background: transparent; }}
    ::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 999px; }}
    ::-webkit-scrollbar-thumb:hover {{ background: var(--muted-2); }}

    /* === Plotly container === */
    [data-testid="stPlotlyChart"] {{
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: .8rem;
    }}

    /* === Forms === */
    [data-testid="stForm"] {{ background: transparent; border: none; padding: 0; }}
    .stCaption, [data-testid="stCaptionContainer"] {{ color: var(--muted) !important; }}

    /* =========================================================
       ARTEMIS COMPONENTS
       ========================================================= */

    .artemis-shell {{ padding: 0; }}

    .artemis-card {{
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 1.05rem 1.2rem;
        backdrop-filter: blur(8px);
    }}

    .artemis-kpi {{
        background: linear-gradient(135deg, var(--card), var(--card-soft));
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 1.05rem 1.2rem;
        height: 100%;
        position: relative;
        overflow: hidden;
        transition: transform .15s ease, border-color .15s ease;
    }}
    .artemis-kpi::before {{
        content: "";
        position: absolute; inset: 0;
        background: linear-gradient(135deg, rgba(124,58,237,0.08), transparent 60%);
        pointer-events: none;
    }}
    .artemis-kpi:hover {{ transform: translateY(-2px); border-color: rgba(124,58,237,0.35); }}
    .artemis-kpi .icon {{
        width: 36px; height: 36px; border-radius: 10px;
        display: flex; align-items: center; justify-content: center;
        background: rgba(124,58,237,0.15);
        color: var(--primary);
        font-size: 1.05rem;
        margin-bottom: .55rem;
    }}
    .artemis-kpi .label {{
        font-size: .72rem; font-weight: 500;
        color: var(--muted);
        text-transform: uppercase; letter-spacing: .08em;
        margin: 0;
    }}
    .artemis-kpi .value {{
        font-size: 1.65rem; font-weight: 700;
        color: var(--text);
        margin: .25rem 0 0 0; line-height: 1.15;
        word-break: break-word;
    }}
    .artemis-kpi .delta {{
        font-size: .8rem; color: var(--success);
        font-weight: 500; margin-top: .35rem;
    }}
    .artemis-kpi .delta.neg {{ color: var(--danger); }}

    .artemis-header {{
        margin-bottom: 1.2rem;
        padding-bottom: .85rem;
        border-bottom: 1px solid var(--border);
    }}
    .artemis-header .eyebrow {{
        color: var(--primary);
        font-size: .72rem; font-weight: 700;
        text-transform: uppercase; letter-spacing: .12em;
    }}
    .artemis-header h1 {{
        margin: .3rem 0 .4rem 0;
        font-size: 1.85rem;
        background: linear-gradient(135deg, var(--text), var(--primary));
        -webkit-background-clip: text; background-clip: text;
        -webkit-text-fill-color: transparent;
        display: inline-block;
    }}
    .artemis-header p {{ color: var(--muted); margin: 0; font-size: .98rem; }}
    .artemis-header .badge {{
        display: inline-block; margin-left: .6rem;
        padding: .2rem .6rem;
        background: rgba(16,185,129,0.15);
        color: var(--success);
        border: 1px solid rgba(16,185,129,0.35);
        border-radius: 999px;
        font-size: .7rem; font-weight: 600;
        letter-spacing: .04em; vertical-align: middle;
        -webkit-text-fill-color: var(--success);
    }}

    .artemis-eyebrow {{
        color: var(--primary); font-size: .72rem;
        font-weight: 700; text-transform: uppercase;
        letter-spacing: .12em;
    }}
    .artemis-muted {{ color: var(--muted); }}

    .artemis-insight {{
        background: linear-gradient(135deg, rgba(124,58,237,0.10), rgba(6,182,212,0.08));
        border-left: 3px solid var(--primary);
        border-radius: 10px;
        padding: .85rem 1.1rem;
        margin: .6rem 0;
        color: var(--text);
        font-size: .93rem;
    }}
    .artemis-insight strong {{ color: var(--text); }}

    .artemis-status {{
        display: inline-flex; align-items: center; gap: .4rem;
        padding: .25rem .7rem;
        border-radius: 999px;
        font-size: .78rem; font-weight: 600;
        letter-spacing: .02em;
    }}
    .artemis-status .dot {{
        width: 6px; height: 6px; border-radius: 50%;
        background: currentColor;
        box-shadow: 0 0 8px currentColor;
    }}
    .artemis-status.success {{ background: rgba(16,185,129,0.12); color: var(--success); border: 1px solid rgba(16,185,129,0.35); }}
    .artemis-status.warning {{ background: rgba(245,158,11,0.12); color: var(--warning); border: 1px solid rgba(245,158,11,0.35); }}
    .artemis-status.danger  {{ background: rgba(239,68,68,0.12);  color: var(--danger);  border: 1px solid rgba(239,68,68,0.35); }}
    .artemis-status.muted   {{ background: rgba(148,163,184,0.12);color: var(--muted);   border: 1px solid var(--border); }}

    .artemis-section-title {{
        font-size: 1.05rem; font-weight: 600;
        color: var(--text);
        margin: .8rem 0 .6rem 0;
        display: flex; align-items: center; gap: .55rem;
    }}
    .artemis-section-title .accent {{
        width: 4px; height: 18px; border-radius: 4px;
        background: linear-gradient(180deg, var(--primary), var(--cyan));
    }}

    .artemis-pill {{
        display: inline-block;
        padding: .25rem .7rem;
        border-radius: 999px;
        background: var(--card-soft);
        border: 1px solid var(--border);
        font-size: .76rem; color: var(--text);
        font-weight: 500;
    }}

    .artemis-topbar {{
        display: flex; align-items: center; justify-content: space-between;
        padding: .6rem 0; margin-bottom: .4rem;
    }}

    .artemis-footer-note {{
        margin-top: 1.2rem;
        font-size: .78rem;
        color: var(--muted-2);
        text-align: center;
    }}

    /* === Login premium === */
    .artemis-login-shell {{
        position: relative;
        overflow: hidden;
        border-radius: 20px;
        padding: 2.2rem;
        background:
            radial-gradient(circle at 20% 20%, rgba(124,58,237,0.25), transparent 50%),
            radial-gradient(circle at 80% 80%, rgba(6,182,212,0.18), transparent 50%),
            linear-gradient(135deg, var(--bg-secondary), var(--card));
        border: 1px solid var(--border);
        min-height: 560px;
    }}
    .artemis-login-shell::after {{
        content: "";
        position: absolute; top: -50px; right: -50px;
        width: 220px; height: 220px;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(124,58,237,0.35), transparent 70%);
        filter: blur(40px);
        pointer-events: none;
    }}

    .artemis-login-card {{
        background: var(--glass-bg);
        border: 1px solid var(--glass-border);
        border-radius: 18px;
        padding: 1.8rem;
        backdrop-filter: blur(14px);
        -webkit-backdrop-filter: blur(14px);
        box-shadow: 0 20px 50px rgba(0,0,0,0.35);
    }}
    .artemis-login-card h2 {{ margin: 0 0 .3rem 0; font-size: 1.4rem; }}

    .artemis-feature {{
        display: flex; align-items: flex-start; gap: .7rem;
        padding: .55rem 0;
    }}
    .artemis-feature-icon {{
        width: 32px;
        height: 32px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: rgba(124,58,237,0.18);
        color: var(--primary);
        flex-shrink: 0;
    }}
    .artemis-feature .text {{
        color: var(--text); font-size: .92rem; line-height: 1.35;
    }}
    .artemis-feature .text small {{
        display: block;
        color: var(--muted);
        font-size: .78rem;
        margin-top: .1rem;
    }}

    /* === Sidebar account === */
    .artemis-account {{
        padding: .85rem;
        border-radius: 12px;
        background: var(--card);
        border: 1px solid var(--border);
        margin-bottom: .8rem;
    }}
    .artemis-account .label {{
        font-size: .68rem; color: var(--muted);
        text-transform: uppercase; letter-spacing: .08em;
    }}
    .artemis-account .email {{
        font-weight: 600; color: var(--text);
        margin-top: .2rem; font-size: .86rem;
        word-break: break-all;
    }}
    .artemis-account .role {{
        margin-top: .4rem;
        display: inline-block;
        padding: .15rem .55rem;
        border-radius: 999px;
        background: rgba(124,58,237,0.18);
        color: var(--primary);
        font-size: .7rem; font-weight: 600;
        letter-spacing: .04em;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


# =========================================================
# SIDEBAR
# =========================================================

def render_sidebar(user) -> None:
    """Sidebar premium : compte, switch thème, logout. PAS de navigation (st.navigation gère)."""
    with st.sidebar:
        email = get_user_email(user)
        admin = is_admin(user)
        role_html = '<span class="role">Admin</span>' if admin else ""

        st.markdown(
            f"""
            <div class="artemis-account">
                <div class="label">Compte actif</div>
                <div class="email">{email}</div>
                {role_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Theme toggle
        current_mode = get_theme_mode()
        labels = ["Sombre", "Clair"]
        current_label = "Sombre" if current_mode == "dark" else "Clair"
        choice = st.radio(
            "Apparence",
            labels,
            index=labels.index(current_label),
            horizontal=True,
            key="theme_radio_sidebar",
        )
        new_mode = "dark" if choice == "Sombre" else "light"
        if new_mode != st.session_state.get("theme_mode"):
            st.session_state["theme_mode"] = new_mode
            st.rerun()

        st.markdown("")
        if st.button("🚪 Se déconnecter", use_container_width=True):
            logout()
            st.rerun()

        st.markdown(
            '<div class="artemis-footer-note">Artemis · v1.1 · © 2026</div>',
            unsafe_allow_html=True,
        )


# =========================================================
# COMPONENTS
# =========================================================

def page_header(title: str, subtitle: str = "", eyebrow: str = "", badge: str | None = None) -> None:
    eyebrow_html = f'<div class="eyebrow">{eyebrow}</div>' if eyebrow else ""
    badge_html = f'<span class="badge">{badge}</span>' if badge else ""
    subtitle_html = f"<p>{subtitle}</p>" if subtitle else ""
    st.markdown(
        f"""
        <div class="artemis-header">
            {eyebrow_html}
            <h1>{title}</h1>{badge_html}
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_title(text: str) -> None:
    st.markdown(
        f"""
        <div class="artemis-section-title">
            <span class="accent"></span><span>{text}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi_card(label: str, value, delta: str = "", positive: bool = True, icon: str | None = None) -> None:
    icon_html = f'<div class="icon">{icon}</div>' if icon else ""
    delta_class = "delta" if positive else "delta neg"
    delta_html = f'<div class="{delta_class}">{delta}</div>' if delta else ""

    html = f"""
<div class="artemis-kpi">
  {icon_html}
  <p class="label">{label}</p>
  <p class="value">{value}</p>
  {delta_html}
</div>
"""
    st.markdown(html, unsafe_allow_html=True)


def metric_card(label: str, value, help_text: str | None = None) -> None:
    """Variante sobre du KPI card (sans icône ni delta)."""
    help_html = (
        f'<div style="font-size:0.8rem;color:var(--muted);margin-top:0.3rem;">{help_text}</div>'
        if help_text else ""
    )
    st.markdown(
        f"""
        <div class="artemis-kpi">
            <p class="label">{label}</p>
            <p class="value">{value}</p>
            {help_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def insight(text: str) -> None:
    st.markdown(
        f'<div class="artemis-insight">💡 <strong>Insight</strong> · {text}</div>',
        unsafe_allow_html=True,
    )


def status_badge(status: str) -> str:
    s = (status or "").lower()
    mapping = {
        "success":     ("success", "Success"),
        "ok":          ("success", "OK"),
        "healthy":     ("success", "Healthy"),
        "running":     ("warning", "Running"),
        "in_progress": ("warning", "In progress"),
        "warning":     ("warning", "Warning"),
        "error":       ("danger",  "Error"),
        "failed":      ("danger",  "Failed"),
    }
    cls, label = mapping.get(s, ("muted", status or "Unknown"))
    return f'<span class="artemis-status {cls}"><span class="dot"></span>{label}</span>'


def pipeline_status_card(title: str, status: str, detail: str = "") -> None:
    badge = status_badge(status)
    detail_html = (
        f'<div class="artemis-muted" style="margin-top:.4rem;font-size:.85rem;">{detail}</div>'
        if detail else ""
    )
    st.markdown(
        f"""
        <div class="artemis-card">
            <div style="display:flex;align-items:center;justify-content:space-between;">
                <div style="font-weight:600;">{title}</div>
                {badge}
            </div>
            {detail_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# PLOTLY
# =========================================================

def style_plotly(fig, height: int = 400):
    mode = get_theme_mode()
    theme = THEMES[mode]

    axis_text = "#CBD5E1" if mode == "dark" else "#334155"
    grid = "rgba(255,255,255,0.08)" if mode == "dark" else "rgba(15,23,42,0.10)"
    legend_bg = "rgba(17,24,39,0.65)" if mode == "dark" else "rgba(255,255,255,0.92)"

    fig.update_layout(
        template="plotly_dark" if mode == "dark" else "plotly_white",
        height=height,

        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",

        font=dict(
            family="Inter, sans-serif",
            size=12,
            color=axis_text,
        ),

        legend=dict(
            bgcolor=legend_bg,
            bordercolor=theme["border"],
            borderwidth=1,
            font=dict(
                color=axis_text,
                size=11
            ),
        ),

        hoverlabel=dict(
            bgcolor=theme["card"],
            bordercolor=theme["primary"],
            font=dict(
                color=theme["text"],
                size=12
            ),
        ),
    )

    fig.update_xaxes(
        tickfont=dict(color=axis_text),
        title_font=dict(color=axis_text),
        gridcolor=grid,
    )

    fig.update_yaxes(
        tickfont=dict(color=axis_text),
        title_font=dict(color=axis_text),
        gridcolor=grid,
    )

    return fig