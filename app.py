import streamlit as st

st.set_page_config(
    page_title="Artemis SaaS",
    page_icon="🚀",
    layout="wide"
)

# SESSION
if "user" not in st.session_state:
    st.session_state["user"] = None

# NAVIGATION
if st.session_state["user"] is None:

    pages = [
        st.Page(
            "pages/1_Connexion.py",
            title="Connexion",
            icon="🔐"
        )
    ]

else:

    pages = [
        st.Page(
            "pages/2_Dashboard.py",
            title="Dashboard",
            icon="📊"
        ),

        st.Page(
            "pages/3_Map_Mondiale.py",
            title="Carte mondiale",
            icon="🌍"
        ),

        st.Page(
            "pages/4_Space_Race.py",
            title="Space Race",
            icon="🏁"
        )
    ]

pg = st.navigation(pages)
pg.run()