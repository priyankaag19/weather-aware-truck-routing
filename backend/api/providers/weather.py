"""Hourly forecasts from Open-Meteo (free, no key, multi-location batching)."""
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone

import requests
from django.conf import settings
from django.core.cache import cache

from ..errors import ProviderError

BATCH_SIZE = 50
CACHE_TTL = 30 * 60
HOURLY = "wind_speed_10m,wind_gusts_10m,rain,showers,snowfall"


@dataclass
class Series:
    """Hourly wind (mph), rain (in/hr) and snow (in/hr), starting at `start` (UTC)."""

    start: datetime
    wind: list
    rain: list
    snow: list

    def at(self, when):
        """Weather at the nearest forecast hour to `when` (clamped to the fetched range)."""
        idx = round((when - self.start).total_seconds() / 3600)
        idx = max(0, min(len(self.wind) - 1, idx))
        return self.wind[idx], self.rain[idx], self.snow[idx]


def _key(point, start, end):
    return f"wx:{point[0]:.2f}:{point[1]:.2f}:{start}:{end}:{settings.WIND_METRIC}"


def _request(points, start_date, end_date):
    params = {
        "latitude": ",".join(f"{p[0]:.2f}" for p in points),
        "longitude": ",".join(f"{p[1]:.2f}" for p in points),
        "hourly": HOURLY,
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",  # also makes snowfall inches
        "timezone": "GMT",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    }
    last = None
    for attempt in range(3):
        try:
            r = requests.get(
                settings.OPEN_METEO_URL, params=params,
                headers={"User-Agent": settings.HTTP_USER_AGENT}, timeout=30,
            )
            if r.status_code == 429:
                time.sleep(1.5 * (attempt + 1))
                last = "rate limited"
                continue
            if r.status_code != 200:
                raise ProviderError(f"Weather service error ({r.status_code}): {r.text[:200]}")
            payload = r.json()
            break
        except requests.RequestException as exc:
            last = str(exc)
            time.sleep(0.8)
    else:
        raise ProviderError(f"Weather service unavailable: {last}")

    locations = payload if isinstance(payload, list) else [payload]
    wind_key = "wind_gusts_10m" if settings.WIND_METRIC == "gusts" else "wind_speed_10m"
    out = []
    for loc in locations:
        h = loc["hourly"]
        start = datetime.fromisoformat(h["time"][0]).replace(tzinfo=timezone.utc)
        out.append(
            Series(
                start=start,
                wind=[v or 0.0 for v in h[wind_key]],
                rain=[(a or 0.0) + (b or 0.0) for a, b in zip(h["rain"], h["showers"])],
                snow=[v or 0.0 for v in h["snowfall"]],
            )
        )
    return out


def fetch_series(points, start_date, end_date):
    """points: iterable of (lat, lng). Returns {(round(lat,2), round(lng,2)): Series}."""
    unique = list(dict.fromkeys((round(lat, 2), round(lng, 2)) for lat, lng in points))
    result, missing = {}, []
    for p in unique:
        hit = cache.get(_key(p, start_date, end_date))
        if hit is not None:
            result[p] = hit
        else:
            missing.append(p)

    chunks = [missing[i : i + BATCH_SIZE] for i in range(0, len(missing), BATCH_SIZE)]
    if chunks:
        with ThreadPoolExecutor(max_workers=4) as pool:
            responses = list(pool.map(lambda c: _request(c, start_date, end_date), chunks))
        for chunk, series_list in zip(chunks, responses):
            for p, s in zip(chunk, series_list):
                result[p] = s
                cache.set(_key(p, start_date, end_date), s, CACHE_TTL)
    return result
