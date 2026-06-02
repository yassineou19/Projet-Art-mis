"""Backfill historique des lancements.

À lancer manuellement. Respecte la limite API avec une pause entre les appels.
"""

import time
import os

import requests

from src.ingestion.pipeline import run_pipeline


SLEEP_SECONDS = int(os.getenv("BACKFILL_SLEEP_SECONDS", "30"))
MAX_RUNS = int(os.getenv("BACKFILL_RUNS", "20"))
RATE_LIMIT_SLEEP_SECONDS = int(os.getenv("BACKFILL_RATE_LIMIT_SLEEP_SECONDS", "300"))


if __name__ == "__main__":
    for i in range(MAX_RUNS):
        print(f"\n--- Backfill run {i + 1}/{MAX_RUNS} ---")

        try:
            run_pipeline()
        except requests.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else None
            if status_code == 429:
                print(
                    "Limite API atteinte. "
                    f"Pause de {RATE_LIMIT_SLEEP_SECONDS} secondes avant de reprendre. "
                    "Vous pouvez aussi augmenter BACKFILL_SLEEP_SECONDS."
                )
                time.sleep(RATE_LIMIT_SLEEP_SECONDS)
                continue
            raise

        if i < MAX_RUNS - 1:
            print(f"Pause {SLEEP_SECONDS} secondes avant le prochain batch...")
            time.sleep(SLEEP_SECONDS)

    print("Backfill terminé.")
