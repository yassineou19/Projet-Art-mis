import pandas as pd
from src.database import get_connection

def load_data(query: str):
    conn = get_connection()
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def load_dashboard_data():
    return {
        "launches_by_year": load_data("select * from launches_by_year"),
        "top_agencies": load_data("select * from top_agencies"),
        "launches_by_country": load_data("select * from launches_by_country"),
        "growth": load_data("select * from launches_growth_by_year")
    }