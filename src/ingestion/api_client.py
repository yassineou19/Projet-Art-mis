"""Small helpers for The Space Devs API calls."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

import requests


API_KEY = os.getenv("THESPACEDEVS_API_KEY")
BASE_URL = "https://ll.thespacedevs.com/2.3.0"
THROTTLE_URL = f"{BASE_URL}/api-throttle/"
REQUEST_TIMEOUT_SECONDS = int(os.getenv("THESPACEDEVS_TIMEOUT_SECONDS", "60"))
REQUEST_MAX_ATTEMPTS = int(os.getenv("THESPACEDEVS_MAX_ATTEMPTS", "3"))
RETRYABLE_STATUS_CODES = {500, 502, 503, 504}


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


def _get_json(url: str, params: dict | None = None) -> dict:
    last_error: Exception | None = None
    for attempt in range(1, REQUEST_MAX_ATTEMPTS + 1):
        try:
            response = requests.get(
                url,
                params=params,
                headers=auth_headers(),
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            if response.status_code in RETRYABLE_STATUS_CODES and attempt < REQUEST_MAX_ATTEMPTS:
                time.sleep(5 * attempt)
                continue
            response.raise_for_status()
            return response.json()
        except (requests.Timeout, requests.ConnectionError) as error:
            last_error = error
            if attempt >= REQUEST_MAX_ATTEMPTS:
                raise
            print(
                "The Space Devs API request failed temporarily "
                f"({type(error).__name__}). Retry {attempt}/{REQUEST_MAX_ATTEMPTS}."
            )
            time.sleep(5 * attempt)

    if last_error is not None:
        raise last_error
    raise RuntimeError("The Space Devs API request failed without a response.")


def fetch_launches(limit: int = 260, offset: int = 0) -> dict:
    """Récupère une seule page de lancements."""
    return _get_json(
        f"{BASE_URL}/launches/",
        params={
            "limit": limit,
            "offset": offset,
        },
    )


def fetch_previous_launches(limit: int = 100) -> dict:
    """Récupère les derniers lancements passés."""
    return _get_json(
        f"{BASE_URL}/launches/previous/",
        params={"limit": limit},
    )


def fetch_upcoming_launches(limit: int = 100) -> dict:
    """Récupère les prochains lancements planifiés."""
    return _get_json(
        f"{BASE_URL}/launches/upcoming/",
        params={"limit": limit},
    )


def get_api_quota() -> ApiQuota:
    payload = _get_json(THROTTLE_URL)
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
