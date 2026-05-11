import streamlit as st
from src.auth import login, signup

# SI DÉJÀ CONNECTÉ
if st.session_state["user"] is not None:
    st.rerun()

st.title("🚀 Artemis")

st.subheader(
    "Plateforme SaaS d’analyse spatiale"
)

st.write(
    "Connectez-vous pour accéder aux dashboards avancés "
    "et aux analyses des lancements spatiaux."
)

mode = st.radio(
    "Choisir une action",
    ["Connexion", "Inscription"]
)

email = st.text_input("Email")

password = st.text_input(
    "Mot de passe",
    type="password"
)

# CONNEXION
if mode == "Connexion":

    if st.button(
        "Se connecter",
        use_container_width=True
    ):

        try:

            response = login(email, password)

            if response.user:

                st.session_state["user"] = response.user

                st.success(
                    "Connexion réussie ✅"
                )

                st.rerun()

        except Exception:

            st.error(
                "Email ou mot de passe incorrect."
            )

# INSCRIPTION
if mode == "Inscription":

    if st.button(
        "Créer un compte",
        use_container_width=True
    ):

        try:

            response = signup(email, password)

            if response.user:

                st.success(
                    "Compte créé avec succès ✅"
                )

                st.info(
                    "Vous pouvez maintenant vous connecter."
                )

        except Exception:

            st.error(
                "Erreur lors de la création du compte."
            )