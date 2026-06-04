"""Page de connexion / inscription inspiree de la maquette Artemis."""
import streamlit as st
from streamlit.components.v1 import html

from src.auth import (
    login,
    request_password_reset,
    set_recovery_session,
    signup,
    update_password,
)
from src.profiles import (
    FALLBACK_SUBSCRIPTION_PLANS,
    create_user_profile,
    load_subscription_plans,
    load_user_profile,
)


html(
    """
    <script>
    const hash = window.location.hash;
    if (hash && hash.includes("access_token") && hash.includes("refresh_token")) {
      const params = new URLSearchParams(hash.slice(1));
      const target = new URL(window.location.href);
      target.hash = "";
      for (const [key, value] of params.entries()) {
        target.searchParams.set(key, value);
      }
      window.location.replace(target.toString());
    }
    </script>
    """,
    height=0,
)


def query_value(name: str) -> str | None:
    value = st.query_params.get(name)
    if isinstance(value, list):
        return value[0] if value else None
    return value


def render_password_recovery() -> None:
    access_token = query_value("access_token")
    refresh_token = query_value("refresh_token")
    reset_type = query_value("type")

    if not access_token or not refresh_token or reset_type != "recovery":
        return

    st.markdown(
        """
        <div class="auth-shell">
          <div class="auth-panel full">
            <h3 class="form-title">Reinitialiser le mot de passe</h3>
            <p class="form-subtitle">Choisissez un nouveau mot de passe Artemis.</p>
        """,
        unsafe_allow_html=True,
    )

    try:
        set_recovery_session(access_token, refresh_token)
    except Exception as error:
        show_config_error(
            "Lien de reinitialisation invalide ou expire. Demandez un nouveau lien.",
            error,
        )
        st.markdown("</div></div>", unsafe_allow_html=True)
        st.stop()

    with st.form("reset_password_form"):
        new_password = st.text_input("Nouveau mot de passe", type="password")
        confirm_password = st.text_input("Confirmer le mot de passe", type="password")
        submit_reset = st.form_submit_button("Mettre a jour le mot de passe", type="primary")

    if submit_reset:
        if len(new_password) < 8:
            st.error("Le mot de passe doit contenir au moins 8 caracteres.")
        elif new_password != confirm_password:
            st.error("Les deux mots de passe ne correspondent pas.")
        else:
            try:
                update_password(new_password)
            except Exception as error:
                show_config_error("Impossible de mettre a jour le mot de passe.", error)
            else:
                st.query_params.clear()
                st.success("Mot de passe mis a jour. Vous pouvez vous connecter.")
                st.stop()

    st.markdown("</div></div>", unsafe_allow_html=True)
    st.stop()


USER_TYPE_OPTIONS = {
    "Passionne d'espace": "space_enthusiast",
    "Journaliste scientifique": "journalist",
}


def show_auth_error(action: str) -> None:
    """Affiche un message propre pour les erreurs d'authentification."""
    st.error(
        f"{action} impossible. Verifiez vos identifiants ou la configuration "
        "Supabase du projet."
    )


def show_config_error(message: str, error: Exception) -> None:
    """Affiche une erreur de configuration sans masquer l'étape qui bloque."""
    st.error(message)
    st.caption(f"{type(error).__name__}: {error}")


@st.cache_data(ttl=300, show_spinner=False)
def get_signup_subscription_plans() -> list[dict]:
    """Charge les offres pour le formulaire d'inscription."""
    try:
        return load_subscription_plans()
    except Exception:
        return FALLBACK_SUBSCRIPTION_PLANS


def format_plan_option(plan: dict) -> str:
    """Libellé lisible d'une offre dans le selectbox."""
    price = int(plan["price_monthly_eur"])
    if price == 0:
        return f"{plan['name']} - gratuit"
    return f"{plan['name']} - {price} EUR/mois"


def render_plan_details(plan: dict) -> None:
    """Affiche le détail de l'offre sélectionnée."""
    price = int(plan["price_monthly_eur"])
    price_label = "Gratuit" if price == 0 else f"{price} EUR / mois"
    features_html = ""

    for item in plan.get("features", []):
        marker = "✓" if item["is_included"] else "Verrouille"
        color = "#86efac" if item["is_included"] else "#c4b5fd"
        opacity = "1" if item["is_included"] else "0.68"
        features_html += (
            f'<div style="display:flex;align-items:flex-start;gap:.55rem;opacity:{opacity};">'
            f'<span style="color:{color};font-weight:800;min-width:4.8rem;">{marker}</span>'
            f"<span>{item['feature']}</span>"
            "</div>"
        )

    st.markdown(
        f"""
        <div style="
            margin:.65rem 0 1rem;
            padding:1rem;
            border:1px solid rgba(202,210,255,.18);
            border-radius:14px;
            background:rgba(12,16,40,.58);
        ">
            <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:1rem;">
                <div>
                    <div style="color:#c277ff;font-size:.75rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase;">
                        Offre selectionnee
                    </div>
                    <div style="color:#fff;font-size:1.15rem;font-weight:850;margin-top:.15rem;">
                        {plan['name']}
                    </div>
                </div>
                <div style="color:#fff;font-weight:850;white-space:nowrap;">
                    {price_label}
                </div>
            </div>
            <p style="color:#b7bdd6;margin:.7rem 0 .8rem;line-height:1.45;">
                {plan['description']}
            </p>
            <div style="display:grid;gap:.45rem;color:#f7f7ff;font-size:.9rem;">
                {features_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


st.markdown(
    """
    <style>
    :root {
        --artemis-bg: #050617;
        --artemis-panel: rgba(17, 20, 46, 0.72);
        --artemis-panel-strong: rgba(19, 22, 52, 0.9);
        --artemis-line: rgba(178, 190, 255, 0.18);
        --artemis-text: #f7f7ff;
        --artemis-muted: #b7bdd6;
        --artemis-purple: #9b4dff;
        --artemis-blue: #3d7bff;
    }

    section[data-testid="stSidebar"],
    header[data-testid="stHeader"],
    div[data-testid="stToolbar"],
    div[data-testid="stDecoration"] {
        display: none !important;
    }

    div[data-testid="stAppViewContainer"] {
        background:
            radial-gradient(circle at 22% 68%, rgba(130, 74, 255, 0.36), transparent 8%),
            radial-gradient(circle at 70% 22%, rgba(76, 96, 255, 0.18), transparent 18%),
            radial-gradient(circle at 52% 92%, rgba(117, 73, 255, 0.32), transparent 16%),
            linear-gradient(135deg, #040511 0%, #07091f 48%, #02030d 100%);
        color: var(--artemis-text);
    }

    div[data-testid="stAppViewContainer"]::before {
        content: "";
        position: fixed;
        inset: 0;
        z-index: 0;
        pointer-events: none;
        background-image:
            radial-gradient(circle, rgba(255,255,255,0.95) 0 1px, transparent 1.5px),
            radial-gradient(circle, rgba(184,139,255,0.72) 0 1px, transparent 1.5px);
        background-size: 88px 88px, 137px 137px;
        background-position: 7px 18px, 42px 11px;
        opacity: 0.42;
    }

    div[data-testid="stAppViewContainer"]::after {
        content: "";
        position: fixed;
        left: -8vw;
        right: -8vw;
        bottom: -50vw;
        height: 45vw;
        z-index: 0;
        pointer-events: none;
        background:
            radial-gradient(ellipse at 50% 8%, rgba(255,255,255,0.9), rgba(177,91,255,0.55) 5%, transparent 11%),
            radial-gradient(ellipse at 50% 0%, rgba(167,107,255,0.8), rgba(40,64,186,0.6) 18%, rgba(18,20,69,0.45) 34%, transparent 62%);
        border-top: 2px solid rgba(183, 137, 255, 0.72);
        filter: drop-shadow(0 -18px 55px rgba(116, 79, 255, 0.42));
        opacity: 0.9;
    }

    .main .block-container {
        max-width: 1240px;
        padding: 3rem 2.25rem 2rem;
        position: relative;
        z-index: 2;
    }

    .artemis-copy {
        padding-top: 2.35rem;
    }

    .artemis-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.7rem 1.2rem;
        border: 1px solid rgba(159, 78, 255, 0.72);
        border-radius: 999px;
        background: rgba(11, 11, 32, 0.48);
        color: #f2eeff;
        font-weight: 700;
        letter-spacing: 0.01em;
        box-shadow: 0 0 26px rgba(128, 67, 255, 0.18);
    }

    .artemis-badge span {
        width: 12px;
        height: 12px;
        display: inline-block;
        border-radius: 999px;
        background: linear-gradient(135deg, #8e3cff, #bd72ff);
    }

    .artemis-logo-row {
        display: flex;
        align-items: center;
        gap: 1rem;
        margin-top: 2.1rem;
    }

    .artemis-mark {
        width: 82px;
        height: 82px;
        display: grid;
        place-items: center;
        border-radius: 26px;
        color: white;
        font-size: 3.1rem;
        background: linear-gradient(145deg, #a45bff, #5729ff 58%, #844cff);
        box-shadow: 0 22px 42px rgba(101, 47, 255, 0.35);
        transform: rotate(-12deg);
    }

    .artemis-title {
        margin: 0;
        font-size: clamp(3.5rem, 6vw, 5.6rem);
        line-height: 0.95;
        color: #fbfbff !important;
        -webkit-text-fill-color: #fbfbff !important;
        text-shadow: 0 10px 32px rgba(127, 95, 255, 0.45);
    }

    .artemis-subtitle {
        margin: 1.5rem 0 0;
        color: #9e4cff !important;
        -webkit-text-fill-color: #9e4cff !important;
        font-size: clamp(1.45rem, 2.3vw, 2rem);
        font-weight: 800;
    }

    .artemis-rule {
        width: 48px;
        height: 4px;
        margin: 1.3rem 0 1.6rem;
        border-radius: 999px;
        background: linear-gradient(90deg, #8d34ff, #4b83ff);
    }

    .artemis-description {
        max-width: 430px;
        margin: 0 0 1.85rem;
        color: #d0d3e7 !important;
        font-size: 1.12rem;
        line-height: 1.55;
    }

    .feature-list {
        display: grid;
        gap: 1rem;
        margin-top: 1.4rem;
    }

    .feature-item {
        display: flex;
        align-items: center;
        gap: 1rem;
    }

    .feature-icon,
    .stat-icon {
        width: 52px;
        height: 52px;
        display: grid;
        place-items: center;
        border-radius: 12px;
        color: #b960ff;
        font-size: 1.55rem;
        background: linear-gradient(145deg, rgba(108, 39, 231, 0.8), rgba(43, 29, 111, 0.85));
        box-shadow: inset 0 0 22px rgba(180, 93, 255, 0.25);
    }

    .feature-item strong {
        display: block;
        color: white !important;
        font-size: 1.02rem;
    }

    .feature-item small {
        color: #b7bdd6 !important;
        font-size: 0.92rem;
    }

    .form-title {
        margin: 0.35rem 0 0.1rem;
        color: #fbfbff !important;
        -webkit-text-fill-color: #fbfbff !important;
        font-size: 1.7rem;
        font-weight: 800;
    }

    .form-subtitle {
        margin: 0 0 1.1rem;
        color: var(--artemis-muted) !important;
        font-size: 1rem;
    }

    .st-key-login_card {
        padding: 2rem 2.15rem;
        border: 1px solid var(--artemis-line);
        border-radius: 24px;
        background: linear-gradient(145deg, rgba(23, 25, 61, 0.88), rgba(6, 8, 29, 0.88));
        box-shadow: 0 28px 80px rgba(0, 0, 0, 0.42);
        backdrop-filter: blur(24px);
    }

    div[data-testid="stTabs"] [role="tablist"] {
        gap: 1.25rem;
        border-bottom: 1px solid rgba(195, 201, 240, 0.14);
    }

    div[data-testid="stTabs"] [role="tab"] {
        flex: 1 1 0;
        justify-content: center;
        color: #f6f2ff !important;
        -webkit-text-fill-color: #f6f2ff !important;
        font-size: 1.04rem;
        font-weight: 800;
        padding: 0.65rem 0 0.9rem;
    }

    div[data-testid="stTabs"] [role="tab"] p,
    div[data-testid="stTabs"] [role="tab"] span {
        color: inherit !important;
        -webkit-text-fill-color: inherit !important;
    }

    div[data-testid="stTabs"] [aria-selected="true"] {
        color: #c277ff !important;
        -webkit-text-fill-color: #c277ff !important;
    }

    div[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
        height: 4px;
        background: linear-gradient(90deg, #9b4dff, #4f85ff);
        border-radius: 999px;
    }

    div[data-testid="stForm"] {
        border: 0;
        padding: 0;
        background: transparent;
    }

    label, div[data-testid="stCheckbox"] label {
        color: #f2f4ff !important;
        -webkit-text-fill-color: #f2f4ff !important;
        font-weight: 700 !important;
    }

    .st-key-login_card,
    .st-key-login_card p,
    .st-key-login_card span,
    .st-key-login_card label,
    .st-key-login_card div[data-testid="stMarkdownContainer"],
    .st-key-login_card div[data-testid="stMarkdownContainer"] p {
        color: #f2f4ff !important;
    }

    .st-key-login_card div[data-baseweb="input"],
    .st-key-login_card div[data-baseweb="base-input"],
    .st-key-login_card div[data-baseweb="input"] > div {
        min-height: 58px;
        border: 1px solid rgba(202, 210, 255, 0.22);
        border-radius: 10px;
        background: rgba(12, 16, 40, 0.72) !important;
        box-shadow: inset 0 0 22px rgba(61, 123, 255, 0.07);
    }

    .st-key-login_card div[data-baseweb="input"]:focus-within {
        border-color: rgba(156, 86, 255, 0.8);
        box-shadow: 0 0 0 3px rgba(155, 77, 255, 0.18);
    }

    .st-key-login_card input {
        background: transparent !important;
        color: white !important;
        -webkit-text-fill-color: white !important;
        caret-color: white !important;
        font-weight: 650;
    }

    .st-key-login_card input:-webkit-autofill,
    .st-key-login_card input:-webkit-autofill:hover,
    .st-key-login_card input:-webkit-autofill:focus {
        box-shadow: 0 0 0 1000px rgba(12, 16, 40, 0.96) inset !important;
        -webkit-box-shadow: 0 0 0 1000px rgba(12, 16, 40, 0.96) inset !important;
        -webkit-text-fill-color: #ffffff !important;
        caret-color: #ffffff !important;
        transition: background-color 9999s ease-in-out 0s;
    }

    .st-key-login_card input::placeholder {
        color: rgba(219, 224, 245, 0.68) !important;
        -webkit-text-fill-color: rgba(219, 224, 245, 0.68) !important;
    }

    div[data-testid="stCheckbox"] {
        margin-top: -0.4rem;
    }

    div[data-testid="stCheckbox"] span {
        border-color: rgba(155, 77, 255, 0.8) !important;
    }

    div[data-testid="stForm"] button[kind="primaryFormSubmit"],
    div[data-testid="stButton"] button {
        min-height: 58px;
        border: 1px solid rgba(177, 129, 255, 0.8);
        border-radius: 10px;
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        font-size: 1.04rem;
        font-weight: 800;
        background: linear-gradient(100deg, #7a27ef 0%, #9b4dff 44%, #3e7bff 100%);
        box-shadow: 0 12px 32px rgba(80, 78, 255, 0.34);
    }

    div[data-testid="stForm"] button[kind="primaryFormSubmit"] p,
    div[data-testid="stButton"] button p {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }

    div[data-testid="stButton"] button[kind="secondary"] {
        background: rgba(12, 16, 40, 0.58);
        border: 1px solid rgba(202, 210, 255, 0.18);
        box-shadow: none;
    }

    .forgot-link {
        display: flex;
        justify-content: flex-end;
        margin-top: -2.1rem;
        margin-bottom: 1rem;
        color: #a250ff !important;
        -webkit-text-fill-color: #a250ff !important;
        font-weight: 700;
    }

    .or-divider {
        display: grid;
        grid-template-columns: 1fr auto 1fr;
        align-items: center;
        gap: 1.4rem;
        margin: 1.35rem 0 1rem;
        color: #aeb5d1 !important;
    }

    .or-divider::before,
    .or-divider::after {
        content: "";
        height: 1px;
        background: rgba(202, 210, 255, 0.18);
    }

    .stats-bar {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 0;
        margin-top: 2.4rem;
        padding: 1.55rem 1.8rem;
        border: 1px solid var(--artemis-line);
        border-radius: 22px;
        background: rgba(17, 20, 46, 0.72);
        backdrop-filter: blur(20px);
        box-shadow: 0 24px 70px rgba(0, 0, 0, 0.34);
    }

    .stat-item {
        display: grid;
        grid-template-columns: 58px 1fr;
        align-items: center;
        gap: 1rem;
        padding: 0 1.4rem;
        border-right: 1px solid rgba(202, 210, 255, 0.14);
    }

    .stat-item:last-child {
        border-right: 0;
    }

    .stat-value {
        color: white;
        font-size: 1.75rem;
        font-weight: 850;
        line-height: 1;
    }

    .stat-value.purple {
        color: #d385ff;
    }

    .stat-label {
        margin-top: 0.45rem;
        color: #c7ccde;
        line-height: 1.45;
        font-size: 0.93rem;
    }

    .artemis-footer {
        margin-top: 2rem;
        display: flex;
        justify-content: center;
        gap: 2rem;
        color: rgba(200, 205, 226, 0.62);
        font-size: 0.88rem;
    }

    .artemis-footer span:not(:first-child) {
        color: #8f4cff;
    }

    @media (max-width: 900px) {
        .main .block-container {
            padding: 1.4rem 1rem 1.5rem;
        }

        .artemis-copy {
            padding-top: 0;
        }

        .artemis-logo-row {
            margin-top: 1.4rem;
        }

        .artemis-mark {
            width: 62px;
            height: 62px;
            font-size: 2.2rem;
        }

        .st-key-login_card {
            padding: 1.35rem;
            border-radius: 18px;
            margin-top: 1.2rem;
        }

        .stats-bar {
            grid-template-columns: repeat(2, minmax(0, 1fr));
            padding: 1rem;
        }

        .stat-item {
            border-right: 0;
            padding: 0.9rem;
        }

        .artemis-footer {
            flex-wrap: wrap;
            gap: 0.8rem 1.2rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


render_password_recovery()

if st.session_state.get("user") is not None:
    st.rerun()


left, right = st.columns([0.92, 1.08], gap="large")

with left:
    st.markdown(
        """
        <div class="artemis-copy">
          <div class="artemis-badge"><span></span>SPACE ANALYTICS · SaaS</div>
          <div class="artemis-logo-row">
            <div class="artemis-mark">▲</div>
            <h1 class="artemis-title">Artemis</h1>
          </div>
          <h2 class="artemis-subtitle">Space Analytics Platform</h2>
          <div class="artemis-rule"></div>
          <p class="artemis-description">
            La plateforme d'analyse des lancements spatiaux pour analystes,
            investisseurs et passionnes.
          </p>
          <div class="feature-list">
            <div class="feature-item">
              <div class="feature-icon">▥</div>
              <div><strong>Dashboards live</strong><small>KPIs & tendances en temps reel</small></div>
            </div>
            <div class="feature-item">
              <div class="feature-icon">◎</div>
              <div><strong>Carte mondiale</strong><small>Sites de lancement & geographie</small></div>
            </div>
            <div class="feature-item">
              <div class="feature-icon">↗</div>
              <div><strong>Space Race</strong><small>Concurrence & performances des agences</small></div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with right:
    with st.container(key="login_card"):
        tab_login, tab_signup = st.tabs(["Connexion", "Creer un compte"])

        with tab_login:
            st.markdown(
                """
                <h3 class="form-title">Accedez a vos dashboards</h3>
                <p class="form-subtitle">Connectez-vous pour continuer</p>
                """,
                unsafe_allow_html=True,
            )
            with st.form("login_form"):
                email = st.text_input(
                    "Email",
                    placeholder="vous@entreprise.com",
                    autocomplete="email",
                )
                password = st.text_input(
                    "Mot de passe",
                    type="password",
                    placeholder="Votre mot de passe",
                    autocomplete="current-password",
                )
                remember = st.checkbox("Se souvenir de moi", value=True)
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
                    except Exception as error:
                        show_config_error(
                            "Authentification Supabase impossible. Verifiez SUPABASE_URL, "
                            "SUPABASE_ANON_KEY ou les identifiants du compte.",
                            error,
                        )
                    else:
                        if not response or not response.user:
                            st.error("Identifiants invalides.")
                        else:
                            try:
                                profile = load_user_profile(response.user.id)
                            except Exception as error:
                                show_config_error(
                                    "Authentification reussie, mais chargement du profil "
                                    "PostgreSQL impossible. Verifiez les secrets DB_* "
                                    "sur Streamlit Cloud.",
                                    error,
                                )
                            else:
                                if profile is None:
                                    st.error(
                                        "Compte authentifie, mais profil Artemis introuvable "
                                        "dans public.user_profiles."
                                    )
                                else:
                                    st.session_state["user"] = response.user
                                    st.session_state["profile"] = profile
                                    st.session_state["remember_me"] = remember
                                    st.success("Connexion reussie. Redirection...")
                                    st.rerun()

            with st.expander("Mot de passe oublie ?"):
                reset_email = st.text_input(
                    "Email du compte",
                    value=email,
                    key="reset_password_email",
                    autocomplete="email",
                )
                if st.button("Envoyer le lien de reinitialisation", use_container_width=True):
                    if not reset_email:
                        st.error("Veuillez renseigner votre email.")
                    else:
                        try:
                            request_password_reset(reset_email)
                        except Exception as error:
                            show_config_error("Impossible d'envoyer le lien de reinitialisation.", error)
                        else:
                            st.success(
                                "Si ce compte existe, un email de reinitialisation vient d'etre envoye."
                            )

            st.markdown('<div class="or-divider">ou</div>', unsafe_allow_html=True)
            if st.button("G  Continuer avec Google", use_container_width=True):
                st.info("La connexion Google n'est pas encore configuree.")

        with tab_signup:
            st.markdown(
                """
                <h3 class="form-title">Creez votre compte</h3>
                <p class="form-subtitle">Rejoignez Artemis Space Analytics</p>
                """,
                unsafe_allow_html=True,
            )
            subscription_plans = get_signup_subscription_plans()
            subscription_plan_options = {
                format_plan_option(plan): plan["id"]
                for plan in subscription_plans
            }

            new_email = st.text_input(
                "Email professionnel",
                key="signup_email",
                placeholder="vous@entreprise.com",
                autocomplete="email",
            )
            new_password = st.text_input(
                "Mot de passe",
                type="password",
                key="signup_pwd",
                placeholder="Au moins 8 caracteres",
                autocomplete="new-password",
            )
            selected_user_type = st.selectbox(
                "Votre profil",
                list(USER_TYPE_OPTIONS.keys()),
                key="signup_user_type",
            )
            selected_subscription_plan = st.selectbox(
                "Votre offre",
                list(subscription_plan_options.keys()),
                key="signup_subscription_plan",
            )
            selected_plan = next(
                plan
                for plan in subscription_plans
                if plan["id"] == subscription_plan_options[selected_subscription_plan]
            )
            render_plan_details(selected_plan)
            create = st.button(
                "Creer mon compte",
                use_container_width=True,
                type="primary",
            )

            if create:
                if not new_email or not new_password:
                    st.error("Veuillez renseigner email et mot de passe.")
                elif len(new_password) < 8:
                    st.error("Le mot de passe doit contenir au moins 8 caracteres.")
                else:
                    try:
                        response = signup(new_email, new_password)
                        if response and response.user:
                            create_user_profile(
                                user_id=response.user.id,
                                email=new_email,
                                user_type=USER_TYPE_OPTIONS[selected_user_type],
                                subscription_plan=subscription_plan_options[
                                    selected_subscription_plan
                                ],
                            )
                            st.success(
                                "Compte cree. Verifiez votre boite mail puis "
                                "connectez-vous via l'onglet Connexion."
                            )
                        else:
                            st.error(
                                "Impossible de creer le compte. "
                                "Cet email est peut-etre deja utilise."
                            )
                    except Exception:
                        show_auth_error("Creation du compte")

st.markdown(
    """
    <div class="stats-bar">
      <div class="stat-item">
        <div class="stat-icon">↗</div>
        <div><div class="stat-value purple">12,842</div><div class="stat-label">Lancements analyses<br>1957 - 2024</div></div>
      </div>
      <div class="stat-item">
        <div class="stat-icon">◎</div>
        <div><div class="stat-value purple">87</div><div class="stat-label">Pays actifs<br>dans le monde</div></div>
      </div>
      <div class="stat-item">
        <div class="stat-icon">⌂</div>
        <div><div class="stat-value">247</div><div class="stat-label">Sites de lancement<br>repertories</div></div>
      </div>
      <div class="stat-item">
        <div class="stat-icon">⌁</div>
        <div><div class="stat-value">68 ans</div><div class="stat-label">De donnees historiques<br>consolidees</div></div>
      </div>
    </div>
    <div class="artemis-footer">
      <span>© 2026 Artemis Platform · Tous droits reserves</span>
      <span>A propos</span>
      <span>Documentation</span>
      <span>Confidentialite</span>
      <span>Contact</span>
    </div>
    """,
    unsafe_allow_html=True,
)
