import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytz

from ml.weather import get_weather_series


class TestWeatherInterpolation(unittest.TestCase):
    @patch("ml.weather.requests.get")
    def test_weather_interpolation(self, mock_get):
        print("\n--- Testing Weather Interpolation (REV F67) ---")

        # 1. Setup mock response with hourly data
        # Request for 2 hours (12:00 and 13:00) should yield 8 slots (12:00 to 13:45)
        # after 15-min interpolation if 14:00 is also provided.
        start_time = datetime(2026, 2, 15, 12, 0, tzinfo=pytz.UTC)
        end_time = datetime(2026, 2, 15, 14, 0, tzinfo=pytz.UTC)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "hourly": {
                "time": [
                    "2026-02-15T12:00",
                    "2026-02-15T13:00",
                    "2026-02-15T14:00",
                ],
                "temperature_2m": [10.0, 20.0, 30.0],
                "cloud_cover": [0.0, 50.0, 100.0],
                "shortwave_radiation": [0.0, 400.0, 800.0],
            }
        }
        mock_get.return_value = mock_resp

        # 2. Call the function
        # Mock config to avoid loading file
        config = {
            "timezone": "UTC",
            "system": {"location": {"latitude": 59.3, "longitude": 18.1}},
        }
        df = get_weather_series(start_time, end_time, config=config)

        # 3. Verify results
        # 12:00 to 14:00 (exclusive) is 8 slots of 15 min
        self.assertEqual(len(df), 8)

        # Check specific interpolation points
        # 12:00 -> 0.0 (exact)
        # 12:15 -> (400-0) * 0.25 = 100.0
        # 12:30 -> (400-0) * 0.50 = 200.0
        # 12:45 -> (400-0) * 0.75 = 300.0
        # 13:00 -> 400.0 (exact)
        # 13:30 -> (800-400) * 0.5 + 400 = 600.0

        rads = df["shortwave_radiation_w_m2"]
        self.assertEqual(rads.iloc[0], 0.0)  # 12:00
        self.assertEqual(rads.iloc[1], 100.0)  # 12:15
        self.assertEqual(rads.iloc[2], 200.0)  # 12:30
        self.assertEqual(rads.iloc[3], 300.0)  # 12:45
        self.assertEqual(rads.iloc[4], 400.0)  # 13:00
        self.assertEqual(rads.iloc[6], 600.0)  # 13:30

        # Check temperatures
        temps = df["temp_c"]
        self.assertEqual(temps.iloc[0], 10.0)  # 12:00
        self.assertEqual(temps.iloc[2], 15.0)  # 12:30
        self.assertEqual(temps.iloc[6], 25.0)  # 13:30 (20 + (30-20)*0.5)

        print("✅ Weather interpolation verified with linear expected values!")


if __name__ == "__main__":
    unittest.main()
