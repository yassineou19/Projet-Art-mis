import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_ANON_KEY")
)

def signup(email: str, password: str):
    return supabase.auth.sign_up({
        "email": email,
        "password": password
    })

def login(email: str, password: str):
    return supabase.auth.sign_in_with_password({
        "email": email,
        "password": password
    })