import streamlit as st
from src.auth import login, signup

st.set_page_config(
    page_title="Connexion",
    page_icon="🔐",
    layout="centered"
)

st.title("🔐 Connexion à Artemis")

mode = st.radio("Choisir une action", ["Connexion", "Inscription"])

email = st.text_input("Email")
password = st.text_input("Mot de passe", type="password")

if mode == "Connexion":
    if st.button("Se connecter"):
        try:
            response = login(email, password)

            if response.user:
                st.session_state["user"] = response.user
                st.success("Connexion réussie ✅")
                st.switch_page("pages/2_Dashboard.py")

        except Exception:
            st.error("Email ou mot de passe incorrect.")

if mode == "Inscription":
    if st.button("Créer un compte"):
        try:
            response = signup(email, password)

            if response.user:
                st.success("Compte créé avec succès ✅")
                st.info("Vous pouvez maintenant vous connecter.")

        except Exception:
            st.error("Erreur lors de la création du compte.")