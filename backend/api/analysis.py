"""Orchestrates routing -> checkpoints -> weather -> risk -> recommendation -> heatmap."""
from datetime import timedelta, timezone

from django.conf import settings

from . import recommend, risk
from .geo import decimate, point_at_mile, sample_miles
from .providers import routing, weather

HEAT_INTERVAL_MI = 10
HEAT_HOURS = 48
HEAT_GRID_DEG = 0.08  # ~5.5 mi: drop heat samples closer than this (shared stretches of road)
ROUTE_LETTERS = "ABC"


def _iso(dt):
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _wx_key(point):
    return (round(point[0], 2), round(point[1], 2))


def _plan_route(route, departure, interval_mi):
    total = route["distance_mi"]
    truck_seconds = route["duration_s"] * settings.TRUCK_SPEED_FACTOR

    def at(mile):
        lat, lng = point_at_mile(route["coords"], route["cum"], mile)
        frac = mile / total if total else 0.0
        return {"mile": mile, "lat": lat, "lng": lng, "eta": departure + timedelta(seconds=truck_seconds * frac)}

    route["truck_seconds"] = truck_seconds
    route["checkpoints"] = [at(m) for m in sample_miles(total, interval_mi)]
    route["heat_samples"] = [at(m) for m in sample_miles(total, HEAT_INTERVAL_MI)]


def analyze(origin, destination, departure, load_lb, interval_mi):
    """origin/destination: (lat, lng). departure: aware datetime."""
    departure = departure.astimezone(timezone.utc)
    routes = routing.get_route_options(origin, destination, count=3)
    for r in routes:
        _plan_route(r, departure, interval_mi)

    # One batched weather fetch covering every checkpoint and heatmap sample.
    points = [(p["lat"], p["lng"]) for r in routes for p in r["checkpoints"] + r["heat_samples"]]
    arrival = max(r["checkpoints"][-1]["eta"] for r in routes)
    window_end = max(arrival, departure + timedelta(hours=HEAT_HOURS))
    series = weather.fetch_series(points, departure.date(), window_end.date())

    out_routes = []
    for idx, r in enumerate(routes):
        label = f"Route {ROUTE_LETTERS[idx]}"
        checkpoints = []
        for p in r["checkpoints"]:
            wind, rain, snow = series[_wx_key((p["lat"], p["lng"]))].at(p["eta"])
            res = risk.classify(wind, rain, snow, load_lb)
            checkpoints.append(
                {
                    "mile": round(p["mile"], 1),
                    "lat": round(p["lat"], 5),
                    "lng": round(p["lng"], 5),
                    "eta": _iso(p["eta"]),
                    "wind_mph": round(wind, 1),
                    "rain_in_hr": round(rain, 3),
                    "snow_in_hr": round(snow, 3),
                    "level": res.name,
                    "level_score": res.level,
                    "load_adjusted": res.load_adjusted,
                    "reasons": res.reasons,
                }
            )
        total = r["distance_mi"]
        coords = decimate(r["coords"], r["cum"], max(0.2, total / 1200))
        out_routes.append(
            {
                "id": f"route-{ROUTE_LETTERS[idx].lower()}",
                "label": label,
                "source": r["source"],
                "roads": r["roads"],
                "distance_mi": round(total, 1),
                "duration_s": round(r["truck_seconds"]),
                "departure": _iso(departure),
                "arrival": _iso(departure + timedelta(seconds=r["truck_seconds"])),
                "geometry": [[round(a, 5), round(b, 5)] for a, b in coords],
                "checkpoints": checkpoints,
                "summary": recommend.summarize(checkpoints),
                "_heat": r["heat_samples"],
            }
        )

    ranked, recommendation = recommend.recommend(out_routes)
    for position, route in enumerate(ranked, start=1):
        route["rank"] = position
        route["recommended"] = position == 1

    # Heatmap: worst-case risk per sample for each hour after departure (0..48).
    seen, heat_points = set(), []
    for route in out_routes:
        for p in route.pop("_heat"):
            cell = (round(p["lat"] / HEAT_GRID_DEG), round(p["lng"] / HEAT_GRID_DEG))
            if cell in seen:
                continue
            seen.add(cell)
            s = series[_wx_key((p["lat"], p["lng"]))]
            levels = [
                risk.classify(*s.at(departure + timedelta(hours=h)), load_lb).level
                for h in range(HEAT_HOURS + 1)
            ]
            heat_points.append({"lat": round(p["lat"], 4), "lng": round(p["lng"], 4), "levels": levels})

    return {
        "request": {"load_lb": load_lb, "interval_mi": interval_mi, "departure": _iso(departure)},
        "routes": out_routes,
        "recommendation": recommendation,
        "heatmap": {"start": _iso(departure), "hours": HEAT_HOURS, "points": heat_points},
        "meta": {
            "routing": "OSRM",
            "weather": "Open-Meteo",
            "truck_speed_factor": settings.TRUCK_SPEED_FACTOR,
            "wind_metric": settings.WIND_METRIC,
        },
    }
