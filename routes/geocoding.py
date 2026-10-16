
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from django.db.migrations import state
import requests

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
MIN_REQUEST_INTERVAL = 1.1
MAX_RETRIES = 5
_last_request_time = 0.0


def _wait_for_rate_limit():
    global _last_request_time

    elapsed = time.monotonic() - _last_request_time
    if elapsed < MIN_REQUEST_INTERVAL:
        time.sleep(MIN_REQUEST_INTERVAL - elapsed)
    _last_request_time = time.monotonic()


def _retry_delay(response, attempt):
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        try:
            return max(0.0, float(retry_after))
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(retry_after)
                return max(
                    0.0,
                    (retry_at - datetime.now(timezone.utc)).total_seconds(),
                )
            except (TypeError, ValueError, OverflowError):
                pass

    return min(60.0, 2 ** (attempt + 1))


def search_location(query):
    for attempt in range(MAX_RETRIES):
        _wait_for_rate_limit()
        response = requests.get(
            NOMINATIM_URL,
            params={
                "q": query,
                "format": "jsonv2",
                "limit": 1,
                "countrycodes": "us",
            },
            headers={
                "User-Agent": "USAroute/1.0 franciscogbonorino@gmail.com"
            },
            timeout=15,
        )

        if response.status_code == 429:
            time.sleep(_retry_delay(response, attempt))
            if attempt < MAX_RETRIES - 1:
                continue

        response.raise_for_status()
        break
    results = response.json()

    if not results:
        return None

    result = results[0]

    return {
        "latitude": float(result["lat"]),
        "longitude": float(result["lon"]),
        "display_name": result.get("display_name", ""),
    }



def get_coordinates(query):
    # Buscamos la ubicación ingresada por el usuario.
    coordinates = search_location(query)

    if coordinates:
        coordinates["match_type"] = "address"
        return coordinates

    # Si no se encontró, probamos agregando USA.
    coordinates = search_location(f"{query}, USA")

    if coordinates:
        coordinates["match_type"] = "address"
        return coordinates

    return {
        "latitude": None,
        "longitude": None,
        "display_name": "",
        "match_type": "not_found",
    }
