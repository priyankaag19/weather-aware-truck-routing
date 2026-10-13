"""Route summaries and the recommendation ranking.

Preference order (from the brief):
  1. fewest Severe miles   2. fewest High miles   3. lowest average risk   4. shortest time
"No Travel" miles are treated as strictly worse than Severe, so they are compared first:
a route you legally/safely cannot drive never beats one you can.

Miles are compared in 1-mile buckets and average risk in 0.05 buckets so floating-point
noise cannot beat a genuine travel-time difference between otherwise-equal routes.
"""
from .risk import LEVEL_NAMES

MILE_TOL = 1.0
AVG_TOL = 0.05


def segment_weights(miles):
    """Miles of road each checkpoint 'speaks for': half the gap to each neighbour."""
    n = len(miles)
    if n < 2:
        return [0.0] * n
    out = []
    for i in range(n):
        prev_m = miles[i - 1] if i > 0 else miles[i]
        next_m = miles[i + 1] if i < n - 1 else miles[i]
        out.append((next_m - prev_m) / 2)
    return out


def summarize(checkpoints):
    """`checkpoints`: dicts with `mile` and `level_score` (0-4)."""
    weights = segment_weights([c["mile"] for c in checkpoints])
    by_level = {name: 0.0 for name in LEVEL_NAMES}
    for c, w in zip(checkpoints, weights):
        by_level[LEVEL_NAMES[c["level_score"]]] += w
    total = sum(weights)
    if total > 0:
        avg = sum(c["level_score"] * w for c, w in zip(checkpoints, weights)) / total
    else:
        avg = float(checkpoints[0]["level_score"]) if checkpoints else 0.0
    worst = max(checkpoints, key=lambda c: c["level_score"]) if checkpoints else None
    return {
        "miles_by_level": {k: round(v, 1) for k, v in by_level.items()},
        "avg_risk": round(avg, 2),
        "max_level": LEVEL_NAMES[worst["level_score"]] if worst else "low",
        "worst_mile": round(worst["mile"], 1) if worst else None,
    }


def rank_key(route):
    m = route["summary"]["miles_by_level"]
    return (
        round(m["no_travel"] / MILE_TOL),
        round(m["severe"] / MILE_TOL),
        round(m["high"] / MILE_TOL),
        round(route["summary"]["avg_risk"] / AVG_TOL),
        route["duration_s"],
    )


CRITERIA = [
    ("No Travel miles", lambda r: r["summary"]["miles_by_level"]["no_travel"], "{:.0f} mi"),
    ("Severe miles", lambda r: r["summary"]["miles_by_level"]["severe"], "{:.0f} mi"),
    ("High miles", lambda r: r["summary"]["miles_by_level"]["high"], "{:.0f} mi"),
    ("average risk", lambda r: r["summary"]["avg_risk"], "{:.2f}"),
    ("travel time", lambda r: r["duration_s"] / 3600, "{:.1f} h"),
]


def rank_routes(routes):
    return sorted(routes, key=rank_key)


def recommend(routes):
    """Returns (ranked_routes, recommendation dict)."""
    ranked = rank_routes(routes)
    best = ranked[0]
    fastest = min(routes, key=lambda r: r["duration_s"])
    blocked = best["summary"]["miles_by_level"]["no_travel"] >= MILE_TOL

    reasons = []
    for other in ranked[1:]:
        kb, ko = rank_key(best), rank_key(other)
        idx = next((i for i in range(len(kb)) if kb[i] != ko[i]), len(kb) - 1)
        name, getter, fmt = CRITERIA[idx]
        reasons.append(
            f"vs {other['label']}: {name} {fmt.format(getter(best))} vs {fmt.format(getter(other))}"
        )

    if blocked:
        headline = (
            f"Every route crosses No-Travel weather. {best['label']} has the least exposure — "
            "consider delaying departure."
        )
    elif best is fastest:
        headline = f"{best['label']} is both the fastest and the lowest-risk option."
    else:
        extra = round((best["duration_s"] - fastest["duration_s"]) / 60)
        headline = (
            f"{best['label']} adds {extra} min versus {fastest['label']} (fastest) "
            "but has less dangerous weather."
        )
    return ranked, {
        "route_id": best["id"],
        "headline": headline,
        "reasons": reasons,
        "blocked": blocked,
        "order": [r["id"] for r in ranked],
    }
