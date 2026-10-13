from datetime import datetime, timedelta, timezone
from unittest import mock

from django.test import SimpleTestCase

from . import analysis, recommend, risk
from .geo import cumulative_miles, sample_miles
from .providers.weather import Series


def level(wind=0, rain=0, snow=0, load=0):
    return risk.LEVEL_NAMES[risk.classify(wind, rain, snow, load).level]


class RiskTests(SimpleTestCase):
    def test_wind_bands(self):
        cases = [(24.9, "low"), (25, "moderate"), (34.9, "moderate"), (35, "high"),
                 (44.9, "high"), (45, "severe"), (54.9, "severe"), (55, "no_travel")]
        for w, expected in cases:
            self.assertEqual(level(wind=w), expected, w)

    def test_rain_bands(self):
        cases = [(0.09, "low"), (0.10, "moderate"), (0.25, "high"), (0.50, "severe"),
                 (1.00, "severe"), (1.01, "no_travel")]
        for v, expected in cases:
            self.assertEqual(level(rain=v), expected, v)

    def test_snow_bands(self):
        cases = [(0.4, "low"), (0.5, "moderate"), (1.0, "high"), (2.0, "severe"),
                 (3.0, "severe"), (3.1, "no_travel")]
        for v, expected in cases:
            self.assertEqual(level(snow=v), expected, v)

    def test_load_rules(self):
        self.assertEqual(level(wind=55, load=0), "no_travel")
        self.assertEqual(level(wind=50, load=30_001), "no_travel")
        self.assertEqual(level(wind=50, load=30_000), "severe")
        self.assertEqual(level(wind=40, load=40_001), "severe")
        self.assertEqual(level(wind=40, load=40_000), "high")
        self.assertEqual(level(wind=30, load=80_000), "moderate")  # load rules need 35+ mph

    def test_worst_condition_wins(self):
        self.assertEqual(level(wind=10, rain=0.3, snow=2.5), "severe")


class RecommendTests(SimpleTestCase):
    @staticmethod
    def route(rid, scores, duration):
        cps = [{"mile": i * 10.0, "level_score": s} for i, s in enumerate(scores)]
        return {"id": rid, "label": rid, "duration_s": duration, "summary": recommend.summarize(cps)}

    def test_weights_sum_to_distance(self):
        self.assertAlmostEqual(sum(recommend.segment_weights([0, 10, 20, 35])), 35)

    def test_fewer_severe_miles_beats_speed(self):
        fast = self.route("fast", [0, 3, 3, 0], 3600)
        slow = self.route("slow", [0, 2, 2, 0], 7200)
        ranked, rec = recommend.recommend([fast, slow])
        self.assertEqual(rec["route_id"], "slow")

    def test_high_miles_break_severe_ties(self):
        a = self.route("a", [0, 2, 2, 0], 3600)
        b = self.route("b", [0, 1, 1, 0], 5000)
        self.assertEqual(recommend.recommend([a, b])[1]["route_id"], "b")

    def test_equal_weather_picks_fastest(self):
        a = self.route("a", [1, 1, 1], 5000)
        b = self.route("b", [1, 1, 1], 4000)
        self.assertEqual(recommend.recommend([a, b])[1]["route_id"], "b")

    def test_no_travel_is_worse_than_severe(self):
        a = self.route("a", [0, 4, 0], 3000)
        b = self.route("b", [3, 3, 3], 9000)
        self.assertEqual(recommend.recommend([a, b])[1]["route_id"], "b")


class AnalysisTests(SimpleTestCase):
    """End-to-end with routing and weather mocked: windy route A vs calm, slower route B."""

    @staticmethod
    def fake_route(lng, duration):
        coords = [(40 + i * 0.1, lng) for i in range(11)]
        cum = cumulative_miles(coords)
        return {"coords": coords, "cum": cum, "distance_mi": cum[-1], "duration_s": duration,
                "roads": ["I 80"], "source": "test"}

    def test_recommends_calm_route(self):
        dep = datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc)
        routes = [self.fake_route(-100.5, 3600), self.fake_route(-99.0, 4000)]

        def fake_fetch(points, start, end):
            s0 = datetime(start.year, start.month, start.day, tzinfo=timezone.utc)
            n = int((end - start).days + 2) * 24
            out = {}
            for lat, lng in points:
                wind = 50.0 if lng < -99.9 else 10.0
                out[(round(lat, 2), round(lng, 2))] = Series(s0, [wind] * n, [0.0] * n, [0.0] * n)
            return out

        with mock.patch.object(analysis.routing, "get_route_options", return_value=routes), \
             mock.patch.object(analysis.weather, "fetch_series", side_effect=fake_fetch):
            data = analysis.analyze((40, -100), (41, -100), dep, 10_000, 25)

        self.assertEqual(data["recommendation"]["route_id"], "route-b")
        a, b = data["routes"]
        self.assertGreater(a["summary"]["miles_by_level"]["severe"], 0)
        self.assertEqual(b["summary"]["max_level"], "low")
        self.assertEqual(len(data["heatmap"]["points"][0]["levels"]), 49)
        self.assertEqual(a["checkpoints"][0]["mile"], 0.0)

    def test_sample_miles(self):
        self.assertEqual(sample_miles(60, 25), [0.0, 25.0, 50.0, 60.0])
        self.assertEqual(sample_miles(51, 25), [0.0, 25.0, 51.0])  # 50 is within 25% of the end
