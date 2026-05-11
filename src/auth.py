"""Authentification Supabase: signup / login / logout / session helpers."""
import os
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()


@st.cache_resource(show_spinner=False)
def _get_supabase_client() -> Client:
    """Client Supabase mémorisé pour la durée de la session Streamlit."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")
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


def logout() -> None:
    """Déconnecte côté Supabase ET nettoie la session Streamlit."""
    try:
        _get_supabase_client().auth.sign_out()
    except Exception:
        # On ignore les erreurs réseau / token déjà invalide.
        pass
    st.session_state["user"] = None


def get_user():
    """Helper: retourne l'utilisateur courant ou None."""
    return st.session_state.get("user")