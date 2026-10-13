"""Geocoding via OpenStreetMap Nominatim (free, no key; 1 request/sec policy -> debounced + cached)."""
import re

import requests
from django.conf import settings
from django.core.cache import cache

from ..errors import ProviderError

LATLNG = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$")


def search(query, limit=5):
    query = query.strip()
    m = LATLNG.match(query)
    if m:  # allow typing raw coordinates
        lat, lng = float(m.group(1)), float(m.group(2))
        if -90 <= lat <= 90 and -180 <= lng <= 180:
            return [{"label": f"{lat:.4f}, {lng:.4f}", "lat": lat, "lng": lng}]

    key = f"geo:{query.lower()}"
    hit = cache.get(key)
    if hit is not None:
        return hit
    try:
        r = requests.get(
            f"{settings.NOMINATIM_URL}/search",
            params={"q": query, "format": "jsonv2", "limit": limit},
            headers={"User-Agent": settings.HTTP_USER_AGENT},
            timeout=10,
        )
        r.raise_for_status()
    except requests.RequestException as exc:
        raise ProviderError(f"Geocoding service unavailable: {exc}") from exc

    # Nominatim can return several entries at the same spot (e.g. a city and its boundary).
    seen, results = set(), []
    for item in r.json():
        coords = (round(float(item["lat"]), 4), round(float(item["lon"]), 4))
        if coords in seen:
            continue
        seen.add(coords)
        results.append(
            {"label": item["display_name"], "lat": float(item["lat"]), "lng": float(item["lon"])}
        )

    cache.set(key, results, 60 * 60 * 24)
    return results