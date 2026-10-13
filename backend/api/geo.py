"""Small geodesy helpers. Coordinates are (lat, lng) tuples; distances in miles."""
import math
from bisect import bisect_right

EARTH_RADIUS_MI = 3958.7613


def haversine_mi(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS_MI * math.asin(math.sqrt(h))


def bearing_deg(a, b):
    lat1, lat2 = math.radians(a[0]), math.radians(b[0])
    dlon = math.radians(b[1] - a[1])
    y = math.sin(dlon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def offset_point(p, bearing, miles):
    """Point `miles` away from p along `bearing` (degrees)."""
    d = miles / EARTH_RADIUS_MI
    br = math.radians(bearing)
    lat1, lon1 = math.radians(p[0]), math.radians(p[1])
    lat2 = math.asin(math.sin(lat1) * math.cos(d) + math.cos(lat1) * math.sin(d) * math.cos(br))
    lon2 = lon1 + math.atan2(math.sin(br) * math.sin(d) * math.cos(lat1), math.cos(d) - math.sin(lat1) * math.sin(lat2))
    return (math.degrees(lat2), (math.degrees(lon2) + 540) % 360 - 180)


def cumulative_miles(coords):
    cum = [0.0]
    for i in range(1, len(coords)):
        cum.append(cum[-1] + haversine_mi(coords[i - 1], coords[i]))
    return cum


def point_at_mile(coords, cum, mile):
    """Interpolated (lat, lng) at `mile` along the polyline."""
    if mile <= 0:
        return coords[0]
    if mile >= cum[-1]:
        return coords[-1]
    i = bisect_right(cum, mile)
    seg = cum[i] - cum[i - 1]
    t = (mile - cum[i - 1]) / seg if seg > 0 else 0.0
    a, b = coords[i - 1], coords[i]
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def sample_miles(total, interval):
    """Mile markers 0, interval, 2*interval ... and always the destination.

    A final marker closer than 25% of an interval to the end is dropped so the
    last two checkpoints are never crowded together.
    """
    miles = [0.0]
    m = float(interval)
    while m < total:
        if total - m >= interval * 0.25:
            miles.append(m)
        m += interval
    if total > 0:
        miles.append(float(total))
    return miles


def decimate(coords, cum, spacing_mi):
    """Thin a dense polyline for the browser while keeping the endpoints."""
    keep = [0]
    last = 0.0
    for i in range(1, len(coords) - 1):
        if cum[i] - last >= spacing_mi:
            keep.append(i)
            last = cum[i]
    if len(coords) > 1:
        keep.append(len(coords) - 1)
    return [coords[i] for i in keep]
