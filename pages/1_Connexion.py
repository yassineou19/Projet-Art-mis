"""Page de connexion / inscription — hero + formulaire + onglets."""
import streamlit as st
from src.auth import login, signup

# Si l'utilisateur est déjà connecté, on relance la navigation
if st.session_state.get("user") is not None:
    st.rerun()

# Hero
st.markdown(
    """
    <div class="artemis-hero">
      <span class="badge">SPACE ANALYTICS · SaaS</span>
      <h1>Artemis 🚀</h1>
      <p>La plateforme d'analyse des lancements spatiaux pour analystes, investisseurs et passionnés.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Layout centré
left, center, right = st.columns([1, 2, 1])

with center:
    tab_login, tab_signup = st.tabs(["🔐 Connexion", "✨ Créer un compte"])

    # --- Connexion ---
    with tab_login:
        with st.form("login_form"):
            st.markdown("##### Accédez à vos dashboards")
            email = st.text_input(
                "Email",
                placeholder="vous@entreprise.com",
                autocomplete="email",
            )
            password = st.text_input(
                "Mot de passe",
                type="password",
                placeholder="••••••••",
                autocomplete="current-password",
            )
            submit = st.form_submit_button(
                "Se connecter",
                use_container_width=True,
                type="primary",
            )

        if submit:
            if not email or not password:
                st.error("Veuillez renseigner email et mot de passe.")
            else:
                try:
                    response = login(email, password)
                    if response and response.user:
                        st.session_state["user"] = response.user
                        st.success("Connexion réussie. Redirection…")
                        st.rerun()
                    else:
                        st.error("Identifiants invalides.")
                except Exception:
                    st.error("Email ou mot de passe incorrect.")

    # --- Inscription ---
    with tab_signup:
        with st.form("signup_form"):
            st.markdown("##### Créez votre compte gratuit")
            new_email = st.text_input(
                "Email professionnel",
                key="signup_email",
                placeholder="vous@entreprise.com",
            )
            new_password = st.text_input(
                "Mot de passe",
                type="password",
                key="signup_pwd",
                placeholder="Au moins 8 caractères",
            )
            create = st.form_submit_button(
                "Créer mon compte",
                use_container_width=True,
                type="primary",
            )

        if create:
            if not new_email or not new_password:
                st.error("Veuillez renseigner email et mot de passe.")
            elif len(new_password) < 8:
                st.error("Le mot de passe doit contenir au moins 8 caractères.")
            else:
                try:
                    response = signup(new_email, new_password)
                    if response and response.user:
                        st.success(
                            "Compte créé. Vérifiez votre boîte mail puis "
                            "connectez-vous via l'onglet Connexion."
                        )
                    else:
                        st.error(
                            "Impossible de créer le compte. "
                            "Cet email est peut-être déjà utilisé."
                        )
                except Exception:
                    st.error("Erreur lors de la création du compte. Réessayez plus tard.")

    # Pitch valeur
    st.markdown(
        """
        <div style="margin-top: 1.5rem; padding: 1rem;
             border: 1px solid rgba(0,0,0,0.06); border-radius: 12px;
             background: white;">
          <div style="display: flex; gap: 1rem; justify-content: space-around;
               text-align: center; flex-wrap: wrap;">
            <div>
              <div style="font-size: 1.4rem;">📊</div>
              <div style="font-weight: 600; font-size: 0.9rem;">Dashboards live</div>
              <div style="color: #6b7280; font-size: 0.8rem;">KPIs & tendances</div>
            </div>
            <div>
              <div style="font-size: 1.4rem;">🌍</div>
              <div style="font-weight: 600; font-size: 0.9rem;">Carte mondiale</div>
              <div style="color: #6b7280; font-size: 0.8rem;">Sites de lancement</div>
            </div>
            <div>
              <div style="font-size: 1.4rem;">🏁</div>
              <div style="font-weight: 600; font-size: 0.9rem;">Space Race</div>
              <div style="color: #6b7280; font-size: 0.8rem;">Concurrence agences</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )