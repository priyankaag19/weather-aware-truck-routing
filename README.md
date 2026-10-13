# Weather-Aware Truck Routing

React + Django app that compares three driving routes by the weather a truck will actually meet,
**at the time it reaches each checkpoint**, then recommends the safest one.

* **Routing:** OSRM (open-source, no key). Three options: OSRM alternatives, topped up with via-point detours if fewer than three come back.
* **Geocoding:** OpenStreetMap Nominatim (debounced, cached). You can also type `lat,lng`.
* **Weather:** Open-Meteo hourly forecast (no key, batched multi-location requests, cached 30 min).
* **Map:** Leaflet + OpenStreetMap tiles, with a custom canvas heatmap layer.

## Run locally

```bash
# 1. API (http://localhost:8000)
cd backend
python3 -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                     # set HTTP_USER_AGENT contact
python manage.py test                                    # 12 tests, no network needed
python manage.py runserver

# 2. Frontend (http://localhost:5173)
cd frontend
npm install
cp .env.example .env                                     # VITE_API_URL=http://localhost:8000
npm run dev
```

Click **Use example trip** (Chicago → Denver) to try it quickly.

## API

| Endpoint | Purpose |
|---|---|
| `GET /api/health/` | liveness |
| `GET /api/geocode/?q=Denver` | `{results:[{label,lat,lng}]}` |
| `POST /api/analyze/` | body: `origin{lat,lng,label}`, `destination`, `departure` (ISO-8601), `load_lb`, `interval_mi` (10/25/50) |

`/api/analyze/` returns `routes[]` (geometry, checkpoints with ETA + wind/rain/snow + risk, summary),
`recommendation` (route id, headline, reasons), and `heatmap` (sample points with 49 hourly risk levels, 0–48 h after departure).

## How it works (`backend/api/`)

| File | Responsibility |
|---|---|
| `providers/routing.py` | OSRM calls, road-name summary, via-point alternatives, de-duplication |
| `providers/weather.py` | Open-Meteo batching, thread pool, cache, hourly `Series.at(time)` |
| `geo.py` | haversine, interpolation along the polyline, checkpoint mile markers |
| `risk.py` | **risk rules** (thresholds + load rules) |
| `recommend.py` | per-route mile summaries + **ranking** |
| `analysis.py` | orchestration: sample → one weather fetch → classify → rank → heatmap |

### Checkpoints and ETAs
Checkpoints are placed every 10/25/50 miles (plus origin and destination). ETA at a checkpoint is
`departure + route_duration × (miles_so_far / total_miles)`, with route duration multiplied by
`TRUCK_SPEED_FACTOR` (default 1.10) because OSRM's public profile is a car profile. Weather is read from the forecast hour nearest to that ETA.

### Risk rules (`risk.py`)
Each checkpoint takes the worst of its wind, rain and snow levels.

| | Low | Moderate | High | Severe | No Travel |
|---|---|---|---|---|---|
| Wind (mph) | <25 | 25–34 | 35–44 | 45–54 | ≥55 |
| Rain (in/hr) | <0.10 | 0.10–0.25 | 0.25–0.50 | 0.50–1.00 | >1.00 |
| Snow (in/hr) | <0.5 | 0.5–1.0 | 1.0–2.0 | 2.0–3.0 | >3.0 |

Boundary choice: lower bounds are inclusive (wind 25 → Moderate; rain 0.25 → High). No Travel follows the
table's wording exactly, so rain 1.00 and snow 3.0 are still Severe.
Load rules (wind only): ≥55 mph → No Travel for any load; 45–54 mph and load > 30,000 lb → No Travel; 35–44 mph and load > 40,000 lb → Severe.

### Recommendation (`recommend.py`)
Each checkpoint "speaks for" the road halfway to its neighbours, so miles at each level sum to the route length.
Routes are ranked by: **No-Travel miles → Severe miles → High miles → average risk (mile-weighted, 0–4) → travel time.**
No-Travel miles come first because a route you cannot drive should never beat one you can.
Miles are compared in 1-mile buckets and average risk in 0.05 buckets so tiny differences do not outrank a real time saving;
in clear weather the fastest route wins. If every route crosses No-Travel weather the UI says so and suggests delaying.

### Heatmap
The backend samples every route every 10 miles (de-duplicated on a ~5 mi grid) and returns the risk level for each of the next 48 hours
after departure. The browser paints one soft disc per sample on a canvas, lowest risk first, so the worst nearby condition always wins
(additive heat libraries blend overlapping low risks into false reds). The slider only re-draws the canvas (rAF-throttled); it makes no network calls.

## Assumptions and limits
* OSRM has no truck profile (height/weight/hazmat restrictions are not considered); `TRUCK_SPEED_FACTOR` is a rough correction. For production use a truck-aware router (ORS `driving-hgv`, HERE, Valhalla).
* Wind uses Open-Meteo 10 m sustained wind (`WIND_METRIC=gusts` switches to gusts). Snow is Open-Meteo `snowfall` (inches of snow per hour, not water equivalent); rain is `rain + showers`.
* Weather does not feed back into speed, and driver hours-of-service breaks are not modelled.
* Forecasts are available from 24 h in the past to 10 days ahead. ETAs are shown in the browser's time zone.
* The public OSRM and Nominatim servers are fair-use demos. Set `OSRM_BASE_URL` for a self-hosted router.
* Heatmap discs are ~14 mi radius, so it shows corridor conditions, not street-level detail.

