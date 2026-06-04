"""Small helpers for The Space Devs API calls."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

import requests


API_KEY = os.getenv("THESPACEDEVS_API_KEY")
BASE_URL = "https://ll.thespacedevs.com/2.3.0"
THROTTLE_URL = f"{BASE_URL}/api-throttle/"


@dataclass(frozen=True)
class ApiQuota:
    request_limit: int
    frequency_seconds: int
    current_use: int
    next_use_seconds: int

    @property
    def remaining(self) -> int:
        return max(self.request_limit - self.current_use, 0)


def auth_headers() -> dict[str, str]:
    if not API_KEY:
        return {}
    return {"Authorization": f"Token {API_KEY}"}


def fetch_launches(limit: int = 260, offset: int = 0) -> dict:
    """Récupère une seule page de lancements."""
    response = requests.get(
        f"{BASE_URL}/launches/",
        params={
            "limit": limit,
            "offset": offset,
        },
        headers=auth_headers(),
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


def fetch_previous_launches(limit: int = 100) -> dict:
    """Récupère les derniers lancements passés."""
    response = requests.get(
        f"{BASE_URL}/launches/previous/",
        params={"limit": limit},
        headers=auth_headers(),
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


def fetch_upcoming_launches(limit: int = 100) -> dict:
    """Récupère les prochains lancements planifiés."""
    response = requests.get(
        f"{BASE_URL}/launches/upcoming/",
        params={"limit": limit},
        headers=auth_headers(),
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


def get_api_quota() -> ApiQuota:
    response = requests.get(THROTTLE_URL, headers=auth_headers(), timeout=30)
    response.raise_for_status()
    payload = response.json()
    return ApiQuota(
        request_limit=int(payload.get("your_request_limit", 15)),
        frequency_seconds=int(payload.get("limit_frequency_secs", 3600)),
        current_use=int(payload.get("current_use", 0)),
        next_use_seconds=int(payload.get("next_use_secs", 0)),
    )


def wait_for_available_quota(reserved_calls: int = 3) -> ApiQuota:
    quota = get_api_quota()
    available = quota.request_limit - quota.current_use - reserved_calls
    if available > 0:
        return quota

    wait_seconds = max(quota.next_use_seconds, 60)
    print(
        "API quota nearly exhausted: "
        f"{quota.current_use}/{quota.request_limit} used. "
        f"Waiting {wait_seconds}s before the next request."
    )
    time.sleep(wait_seconds)
    return get_api_quota()
