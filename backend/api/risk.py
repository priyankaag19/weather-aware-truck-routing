"""Weather risk classification — the single source of truth for the risk rules.

Boundary convention (the brief's table is ambiguous at the edges):
  * a band's lower bound is inclusive:        wind 25 -> Moderate, 35 -> High, 45 -> Severe
  * "No Travel" uses the brief's own wording:  wind >= 55, rain > 1.00, snow > 3.0
    so rain exactly 1.00 in/hr and snow exactly 3.0 in/hr are still Severe.
"""
from dataclasses import dataclass, field

LOW, MODERATE, HIGH, SEVERE, NO_TRAVEL = range(5)
LEVEL_NAMES = ["low", "moderate", "high", "severe", "no_travel"]
LEVEL_LABELS = ["Low", "Moderate", "High", "Severe", "No Travel"]

# (lower bounds of Moderate/High/Severe, no-travel threshold, no-travel inclusive?)
WIND_RULE = ((25, 35, 45), 55, True)       # mph
RAIN_RULE = ((0.10, 0.25, 0.50), 1.00, False)  # in/hr
SNOW_RULE = ((0.5, 1.0, 2.0), 3.0, False)      # in/hr

HEAVY_LOAD_NO_TRAVEL_LB = 30_000   # with 45-54 mph wind
HEAVY_LOAD_SEVERE_LB = 40_000      # with 35-44 mph wind


def _band(value, rule):
    lows, no_travel, inclusive = rule
    exceeded = value >= no_travel if inclusive else value > no_travel
    if exceeded:
        return NO_TRAVEL
    return sum(value >= b for b in lows)


@dataclass
class RiskResult:
    level: int
    wind_level: int
    rain_level: int
    snow_level: int
    load_adjusted: bool = False
    reasons: list = field(default_factory=list)

    @property
    def name(self):
        return LEVEL_NAMES[self.level]


def classify(wind_mph, rain_in_hr, snow_in_hr, load_lb):
    wind_level = _band(wind_mph, WIND_RULE)
    rain_level = _band(rain_in_hr, RAIN_RULE)
    snow_level = _band(snow_in_hr, SNOW_RULE)
    adjusted = False
    reasons = []

    # Load rules only ever raise the wind level.
    if wind_mph >= 55:
        wind_level = NO_TRAVEL
        reasons.append("Wind ≥ 55 mph: no travel for any load")
    elif wind_mph >= 45 and load_lb > HEAVY_LOAD_NO_TRAVEL_LB:
        wind_level, adjusted = NO_TRAVEL, True
        reasons.append("Wind 45–54 mph with load > 30,000 lb: no travel")
    elif 35 <= wind_mph < 45 and load_lb > HEAVY_LOAD_SEVERE_LB:
        if wind_level < SEVERE:
            wind_level, adjusted = SEVERE, True
        reasons.append("Wind 35–44 mph with load > 40,000 lb: severe")

    for name, lvl, text in (
        ("wind", wind_level, f"wind {wind_mph:.0f} mph"),
        ("rain", rain_level, f"rain {rain_in_hr:.2f} in/hr"),
        ("snow", snow_level, f"snow {snow_in_hr:.2f} in/hr"),
    ):
        if lvl > LOW and not (name == "wind" and reasons):
            reasons.append(f"{LEVEL_LABELS[lvl]}: {text}")

    return RiskResult(
        level=max(wind_level, rain_level, snow_level),
        wind_level=wind_level,
        rain_level=rain_level,
        snow_level=snow_level,
        load_adjusted=adjusted,
        reasons=reasons,
    )
