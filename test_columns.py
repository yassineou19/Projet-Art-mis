import requests
import pandas as pd
import time

BASE_URL = "https://ll.thespacedevs.com/2.2.0/launch/previous/"
LIMIT = 50
offset = 0

all_launches = []
stop = False
max_429_retries = 3
retry_429_count = 0

while not stop:
    url = f"{BASE_URL}?mode=detailed&limit={LIMIT}&offset={offset}"
    print("Requête :", url)

    try:
        response = requests.get(url, timeout=(10, 60))

        if response.status_code == 429:
            retry_429_count += 1
            print(f"Rate limit atteint → pause 60s ({retry_429_count}/{max_429_retries})")
            
            if retry_429_count >= max_429_retries:
                print("Trop de 429 sur cette page → arrêt du script.")
                break

            time.sleep(60)
            continue

        # si la requête passe, on remet le compteur à zéro
        retry_429_count = 0

        response.raise_for_status()
        data = response.json()

    except requests.exceptions.Timeout:
        print("Timeout → pause 10s")
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
        date = launch.get("net")

        if not date:
            continue

        year = date[:4]

        if year == "2025":
            all_launches.append(launch)

        elif year < "2025":
            print("On est arrivé avant 2025 → arrêt du script.")
            stop = True
            break

    offset += LIMIT
    time.sleep(5)

print("Nombre de lancements 2025 récupérés :", len(all_launches))

if all_launches:
    df = pd.json_normalize(all_launches)
    df.to_csv("launches_2025_full_columns.csv", index=False)
    print("CSV créé : launches_2025_full_columns.csv")
    print("Nombre de colonnes :", len(df.columns))
else:
    print("Aucune donnée sauvegardée.")