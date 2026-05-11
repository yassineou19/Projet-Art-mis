import streamlit as st

st.set_page_config(
    page_title="Artemis SaaS",
    page_icon="🚀",
    layout="wide"
)

st.title("🚀 Artemis")
st.subheader("Plateforme SaaS d’analyse des lancements spatiaux")

st.write(
    "Analysez l’évolution de l’industrie spatiale, comparez les agences, "
    "explorez les tendances et accédez à des visualisations interactives."
)

st.info("Connectez-vous depuis le menu à gauche pour accéder au dashboard.")

if "user" in st.session_state:
    st.success(f"Vous êtes connecté avec : {st.session_state['user'].email}")

with st.sidebar:
    st.title("🚀 Artemis")
    st.caption("Plateforme SaaS spatiale")