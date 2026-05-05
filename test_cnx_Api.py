import requests
import csv
import time

BASE_URL = "https://ll.thespacedevs.com/2.2.0/launch/previous/"
LIMIT = 20
MAX_LAUNCHES = 200
OUTPUT_FILE = "historical_launches.csv"

all_rows = []
offset = 0

while len(all_rows) < MAX_LAUNCHES:
    url = f"{BASE_URL}?mode=detailed&limit={LIMIT}&offset={offset}"
    print(f"Requête vers : {url}")

    try:
        response = requests.get(url, timeout=(10, 60))

        if response.status_code == 429:
            print("Rate limit atteint. Pause de 60 secondes...")
            time.sleep(60)
            continue

        response.raise_for_status()
        data = response.json()

    except requests.exceptions.Timeout:
        print("Timeout. Pause de 10 secondes...")
        time.sleep(10)
        continue

    except requests.exceptions.RequestException as e:
        print(f"Erreur API : {e}")
        break

    results = data.get("results", [])

    if not results:
        print("Plus de résultats.")
        break

    for launch in results:
        launch_id = launch.get("id")
        launch_name = launch.get("name")
        launch_date = launch.get("net")

        agency = None
        lsp = launch.get("launch_service_provider")
        if lsp:
            agency = lsp.get("name")

        launch_country = None
        pad = launch.get("pad")
        if pad and pad.get("location"):
            launch_country = pad["location"].get("country_code")

        all_rows.append([
            launch_id,
            launch_name,
            launch_date,
            agency,
            launch_country
        ])

        if len(all_rows) >= MAX_LAUNCHES:
            break

    print(f"{len(all_rows)} lancements récupérés")
    offset += LIMIT
    time.sleep(5)

with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["launch_id", "launch_name", "date", "agency", "launch_country"])
    writer.writerows(all_rows)

print(f"Fichier créé : {OUTPUT_FILE}")