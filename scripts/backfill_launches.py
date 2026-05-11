"""Backfill historique des lancements.

À lancer manuellement. Respecte la limite API avec une pause entre les appels.
"""

import time

from src.ingestion.pipeline import run_pipeline


SLEEP_SECONDS = 240  # 4 minutes
MAX_RUNS = 20        # sécurité: 20 appels max


if __name__ == "__main__":
    for i in range(MAX_RUNS):
        print(f"\n--- Backfill run {i + 1}/{MAX_RUNS} ---")

        run_pipeline()

        if i < MAX_RUNS - 1:
            print(f"Pause {SLEEP_SECONDS} secondes pour respecter la limite API...")
            time.sleep(SLEEP_SECONDS)

    print("Backfill terminé.")