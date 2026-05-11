"""Chargement des données depuis les vues SQL Supabase, avec cache 10 min."""
import pandas as pd
import streamlit as st
from src.database import connection


@st.cache_data(ttl=600, show_spinner=False)
def load_view(view_name: str) -> pd.DataFrame:
    """Charge une vue SQL par son nom (cache 10 minutes)."""
    # Liste blanche basique pour bloquer toute injection éventuelle.
    if not view_name.replace("_", "").isalnum():
        raise ValueError(f"Nom de vue invalide: {view_name}")
    query = f"SELECT * FROM {view_name}"
    with connection() as conn:
        return pd.read_sql(query, conn)


@st.cache_data(ttl=600, show_spinner=False)
def load_data(query: str) -> pd.DataFrame:
    """Compatibilité ascendante: exécute une requête SQL libre."""
    with connection() as conn:
        return pd.read_sql(query, conn)


def load_dashboard_data() -> dict:
    """Charge toutes les vues nécessaires au dashboard en une fois."""
    return {
        "launches_by_year": load_view("launches_by_year"),
        "top_agencies": load_view("top_agencies"),
        "launches_by_country": load_view("launches_by_country"),
        "growth": load_view("launches_growth_by_year"),
    }