"""Route generation via OSRM (open-source routing, no API key).

OSRM returns up to 3 alternatives for a single request. When it returns fewer than three
(common on simple corridors) we synthesise extra options by routing through a via-point
pushed sideways off the primary route, and keep only candidates that are meaningfully
different from what we already have.
"""
import requests
from django.conf import settings

from ..errors import NoRouteError, ProviderError
from ..geo import bearing_deg, cumulative_miles, haversine_mi, offset_point, point_at_mile

METERS_PER_MILE = 1609.344


def _road_summary(route):
    totals = {}
    for leg in route.get("legs", []):
        for step in leg.get("steps", []):
            label = (step.get("ref") or step.get("name") or "").split(";")[0].strip()
            if label:
                totals[label] = totals.get(label, 0.0) + step.get("distance", 0.0)
    return sorted(totals, key=totals.get, reverse=True)[:3]


def _parse(route):
    coords = [(lat, lng) for lng, lat in route["geometry"]["coordinates"]]
    distance_mi = route["distance"] / METERS_PER_MILE
    cum = cumulative_miles(coords)
    scale = distance_mi / cum[-1] if cum[-1] else 1.0  # make mile markers agree with OSRM's distance
    return {
        "coords": coords,
        "cum": [c * scale for c in cum],
        "distance_mi": distance_mi,
        "duration_s": route["duration"],
        "roads": _road_summary(route),
    }


def _osrm(waypoints, alternatives):
    path = ";".join(f"{lng:.6f},{lat:.6f}" for lat, lng in waypoints)
    try:
        r = requests.get(
            f"{settings.OSRM_BASE_URL}/route/v1/driving/{path}",
            params={
                "alternatives": "3" if alternatives else "false",
                "overview": "full",
                "geometries": "geojson",
                "steps": "true",
            },
            headers={"User-Agent": settings.HTTP_USER_AGENT},
            timeout=40,
        )
        data = r.json()
    except (requests.RequestException, ValueError) as exc:
        raise ProviderError(f"Routing service unavailable: {exc}") from exc
    code = data.get("code")
    if code in ("NoRoute", "NoSegment"):
        raise NoRouteError(code)
    if code != "Ok":
        raise ProviderError(f"Routing service error: {data.get('message') or code}")
    return [_parse(rt) for rt in data["routes"]]


def _profile(route, n=24):
    total = route["distance_mi"]
    return [point_at_mile(route["coords"], route["cum"], total * i / (n - 1)) for i in range(n)]


def _similar(a, b):
    if abs(a["distance_mi"] - b["distance_mi"]) / max(a["distance_mi"], 1e-9) > 0.015:
        return False
    return max(haversine_mi(p, q) for p, q in zip(_profile(a), _profile(b))) < 2.0


def _via_candidates(base):
    total = base["distance_mi"]
    offset = min(max(total * 0.12, 4.0), 60.0)
    for frac in (0.5, 0.3, 0.7):
        mile = total * frac
        a = point_at_mile(base["coords"], base["cum"], mile - 0.5)
        b = point_at_mile(base["coords"], base["cum"], mile + 0.5)
        mid = point_at_mile(base["coords"], base["cum"], mile)
        heading = bearing_deg(a, b)
        for side in (90, -90):
            yield offset_point(mid, heading + side, offset)


def get_route_options(origin, destination, count=3):
    """origin/destination are (lat, lng). Returns up to `count` routes, fastest first."""
    routes = _osrm([origin, destination], alternatives=True)[:count]
    for r in routes:
        r["source"] = "osrm-alternative"
    base = routes[0]
    for via in _via_candidates(base):
        if len(routes) >= count:
            break
        try:
            cand = _osrm([origin, via, destination], alternatives=False)[0]
        except (NoRouteError, ProviderError):
            continue
        if cand["distance_mi"] > base["distance_mi"] * 1.6:
            continue  # absurd detour
        if any(_similar(cand, r) for r in routes):
            continue
        cand["source"] = "via-detour"
        routes.append(cand)
    return sorted(routes, key=lambda r: r["duration_s"])
