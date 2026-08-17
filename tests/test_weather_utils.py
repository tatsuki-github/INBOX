from __future__ import annotations

import sys
import unittest
from datetime import date, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from weather_utils import (  # noqa: E402
    build_weather_record,
    degrees_to_direction,
    format_weather_detail_lines,
    format_weather_summary,
    infer_observation_time,
    wmo_to_condition,
)


class WeatherUtilsTests(unittest.TestCase):
    def test_wmo_to_condition(self) -> None:
        self.assertEqual(wmo_to_condition(0), "快晴")
        self.assertEqual(wmo_to_condition(61), "雨（弱）")

    def test_degrees_to_direction(self) -> None:
        self.assertEqual(degrees_to_direction(0), "北")
        self.assertEqual(degrees_to_direction(90), "東")
        self.assertEqual(degrees_to_direction(135), "南東")

    def test_infer_observation_time(self) -> None:
        self.assertEqual(
            infer_observation_time({"title": "岱明朝練", "tags": ["session:morning"]}),
            time(8, 0),
        )
        self.assertEqual(
            infer_observation_time({"title": "岱明夕練", "start_time": "18:00"}),
            time(18, 0),
        )

    def test_build_and_format_weather_record(self) -> None:
        hourly = {
            "weather_code": 1,
            "temperature_2m": 28.4,
            "relative_humidity_2m": 72.0,
            "precipitation": 0.0,
            "wind_speed_10m": 6.2,
            "wind_direction_10m": 135.0,
        }
        record = build_weather_record(date(2026, 7, 21), time(8, 0), hourly)
        self.assertEqual(record["condition"], "晴れ")
        self.assertEqual(record["temperature_c"], 28.4)
        self.assertEqual(record["humidity_pct"], 72)
        self.assertEqual(record["wind_direction"], "南東")

        summary = format_weather_summary(record)
        self.assertIn("玉名市", summary)
        self.assertIn("28.4°C", summary)

        detail = format_weather_detail_lines(record)
        self.assertTrue(any("天気（玉名市）" in line for line in detail))


if __name__ == "__main__":
    unittest.main()
