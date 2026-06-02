from src.ingestion.pipeline import is_rate_limit_error, run_recent_pipeline

if __name__ == "__main__":
    try:
        run_recent_pipeline()
    except Exception as exc:
        if is_rate_limit_error(exc):
            print("Recent ingestion paused: API rate limit reached.")
        else:
            raise
