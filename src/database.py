"""Connexion PostgreSQL (Supabase) via psycopg2."""
import os
from contextlib import contextmanager
import psycopg2
from dotenv import load_dotenv

load_dotenv()


def _config() -> dict:
    return {
        "host": os.getenv("DB_HOST"),
        "dbname": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "port": os.getenv("DB_PORT"),
    }


def get_connection():
    """Ouvre une connexion psycopg2 brute (à fermer manuellement)."""
    return psycopg2.connect(**_config())


@contextmanager
def connection():
    """Context manager: garantit la fermeture, même en cas d'exception."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()