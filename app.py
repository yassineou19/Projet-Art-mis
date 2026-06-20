"""Artemis — Point d'entrée: configuration globale + navigation conditionnelle."""

import streamlit as st

from src.ui import apply_theme, is_admin

st.set_page_config(
    page_title="Artemis · Space Analytics",
    page_icon=":material/orbit:",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "Artemis — SaaS d'analyse des lancements spatiaux."},
)

# === Bootstrap thème (dark par défaut) ===
if "theme_mode" not in st.session_state:
    st.session_state["theme_mode"] = "dark"

apply_theme(mode=st.session_state["theme_mode"])

# === Bootstrap auth ===
if "user" not in st.session_state:
    st.session_state["user"] = None

# === Navigation conditionnelle ===
if st.session_state["user"] is None:
    pages = {
        "Compte": [
            st.Page(
                "pages/1_Connexion.py",
                title="Connexion",
                icon=":material/login:",
                default=True,
            ),
        ],
    }
else:
    public_pages = [
        st.Page(
            "pages/2_Dashboard.py",
            title="Dashboard",
            icon=":material/dashboard:",
            default=True,
        ),
        st.Page(
            "pages/6_Briefing.py",
            title="Briefing",
            icon=":material/article:",
        ),
        st.Page(
            "pages/3_Map_Mondiale.py",
            title="Carte mondiale",
            icon=":material/public:",
        ),
        st.Page(
            "pages/4_Space_Race.py",
            title="Space Race",
            icon=":material/emoji_events:",
        ),
        st.Page(
            "pages/7_Prediction_ML.py",
            title="Prédiction ML",
            icon=":material/model_training:",
        ),
        st.Page(
            "pages/8_Abonnements.py",
            title="Abonnements",
            icon=":material/workspace_premium:",
        ),
    ]

    pages = {"Analytics": public_pages}

    if is_admin(st.session_state["user"]):
        pages["Administration"] = [
            st.Page(
                "pages/5_Pipeline_Monitoring.py",
                title="Data Control Center",
                icon=":material/monitoring:",
            ),
        ]

pg = st.navigation(pages, position="sidebar")
pg.run()
