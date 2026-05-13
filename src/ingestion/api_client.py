"""Client API The Space Devs."""

import requests

BASE_URL = "https://ll.thespacedevs.com/2.3.0"


def fetch_launches(limit: int = 260, offset: int = 0) -> dict:
    """Récupère une seule page de lancements."""
    response = requests.get(
        f"{BASE_URL}/launches/",
        params={
            "limit": limit,
            "offset": offset,
        },
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


def fetch_previous_launches(limit: int = 100) -> dict:
    """Récupère les derniers lancements passés."""
    response = requests.get(
        f"{BASE_URL}/launches/previous/",
        params={"limit": limit},
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


def fetch_upcoming_launches(limit: int = 100) -> dict:
    """Récupère les prochains lancements planifiés."""
    response = requests.get(
        f"{BASE_URL}/launches/upcoming/",
        params={"limit": limit},
        timeout=30,
    )

    response.raise_for_status()

    return response.json()
