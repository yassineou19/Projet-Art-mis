"""Authentification Supabase: signup / login / logout / session helpers."""
import os
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()


def _setting(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value:
        return value

    try:
        secret_value = st.secrets.get(name)
    except Exception:
        secret_value = None

    return secret_value or default


@st.cache_resource(show_spinner=False)
def _get_supabase_client() -> Client:
    """Client Supabase mémorisé pour la durée de la session Streamlit."""
    url = _setting("SUPABASE_URL")
    key = _setting("SUPABASE_ANON_KEY")
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL et SUPABASE_ANON_KEY doivent être définis dans .env"
        )
    return create_client(url, key)


def signup(email: str, password: str):
    """Crée un nouveau compte utilisateur."""
    return _get_supabase_client().auth.sign_up({
        "email": email,
        "password": password,
    })


def login(email: str, password: str):
    """Authentifie un utilisateur existant."""
    return _get_supabase_client().auth.sign_in_with_password({
        "email": email,
        "password": password,
    })


def get_app_base_url() -> str:
    """URL publique de l'application, utilisée pour les redirects auth."""
    return (_setting("APP_BASE_URL") or "http://localhost:8501").rstrip("/")


def request_password_reset(email: str) -> None:
    """Envoie un email Supabase de réinitialisation du mot de passe."""
    _get_supabase_client().auth.reset_password_for_email(
        email,
        {"redirect_to": get_app_base_url()},
    )


def set_recovery_session(access_token: str, refresh_token: str):
    """Active la session Supabase reçue après un lien de récupération."""
    return _get_supabase_client().auth.set_session(access_token, refresh_token)


def update_password(new_password: str):
    """Met à jour le mot de passe de l'utilisateur en session recovery."""
    return _get_supabase_client().auth.update_user({"password": new_password})


def logout() -> None:
    """Déconnecte côté Supabase ET nettoie la session Streamlit."""
    try:
        _get_supabase_client().auth.sign_out()
    except Exception:
        # On ignore les erreurs réseau / token déjà invalide.
        pass
    st.session_state["user"] = None
    st.session_state["profile"] = None


def get_user():
    """Helper: retourne l'utilisateur courant ou None."""
    return st.session_state.get("user")
