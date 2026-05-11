"""
Artemis — Plateforme SaaS d'analyse spatiale.
Point d'entrée: configuration globale + navigation conditionnelle.
"""
import streamlit as st
from src.ui import apply_theme

# Doit être le tout premier appel Streamlit
st.set_page_config(
    page_title="Artemis · Space Analytics",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": "Artemis — SaaS d'analyse des lancements spatiaux."
    },
)

# Thème global (CSS injecté une fois pour toutes les pages)
apply_theme()

# Initialisation de la session utilisateur
if "user" not in st.session_state:
    st.session_state["user"] = None

# Navigation conditionnelle (publique vs privée)
if st.session_state["user"] is None:
    pages = {
        "Compte": [
            st.Page(
                "pages/1_Connexion.py",
                title="Connexion",
                icon="🔐",
                default=True,
            ),
        ],
    }
else:
    pages = {
        "Analytics": [
            st.Page(
                "pages/2_Dashboard.py",
                title="Dashboard",
                icon="📊",
                default=True,
            ),
            st.Page(
                "pages/3_Map_Mondiale.py",
                title="Carte mondiale",
                icon="🌍",
            ),
            st.Page(
                "pages/4_Space_Race.py",
                title="Space Race",
                icon="🏁",
            ),
        ],
    }

pg = st.navigation(pages, position="sidebar")
pg.run()