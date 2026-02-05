# Mock the library before importing inputs
import sys
import unittest
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

mock_om = MagicMock()
sys.modules["open_meteo_solar_forecast"] = mock_om

from inputs import _get_forecast_data_async  # noqa: E402


class TestForecastAggregation(unittest.IsolatedAsyncioTestCase):
    async def test_multi_array_aggregation(self):
        print("\n--- Testing Multi-Array Forecast Aggregation ---")

        # 1. Setup mock config with 2 arrays
        config = {
            "timezone": "UTC",
            "system": {
                "location": {"latitude": 59.3, "longitude": 18.1},
                "solar_arrays": [
                    {"name": "Array 1", "azimuth": 180, "tilt": 35, "kwp": 10.0},
                    {"name": "Array 2", "azimuth": 90, "tilt": 35, "kwp": 5.0},
                ],
            },
        }

        # 2. Setup mock price slots (4 slots = 1 hour)
        price_slots = [
            {"start_time": datetime(2024, 6, 21, 12, 0, tzinfo=UTC)},
            {"start_time": datetime(2024, 6, 21, 12, 15, tzinfo=UTC)},
            {"start_time": datetime(2024, 6, 21, 12, 30, tzinfo=UTC)},
            {"start_time": datetime(2024, 6, 21, 12, 45, tzinfo=UTC)},
        ]

        # 3. Setup mock OpenMeteoSolarForecast estimate response
        # The library returns a dictionary of {datetime: watts} where watts is already aggregated
        # but we want to verify that we passed the correct lists to the constructor.
        mock_estimate = MagicMock()
        mock_estimate.watts = {
            datetime(2024, 6, 21, 12, 0, tzinfo=UTC): 1000.0,
            datetime(2024, 6, 21, 12, 15, tzinfo=UTC): 1000.0,
            datetime(2024, 6, 21, 12, 30, tzinfo=UTC): 1000.0,
            datetime(2024, 6, 21, 12, 45, tzinfo=UTC): 1000.0,
        }

        # Configure the mock to return this estimate
        mock_forecast_instance = AsyncMock()
        mock_forecast_instance.estimate.return_value = mock_estimate
        mock_forecast_instance.__aenter__.return_value = mock_forecast_instance
        mock_om.OpenMeteoSolarForecast.return_value = mock_forecast_instance

        # 4. Mock get_load_profile_from_ha to avoid HA calls
        with patch("inputs.get_load_profile_from_ha", return_value=[0.5] * 96):
            # 5. Call the function
            result = await _get_forecast_data_async(price_slots, config)

        # 6. Verify constructor calls
        mock_om.OpenMeteoSolarForecast.assert_called_with(
            latitude=59.3,
            longitude=18.1,
            declination=[35.0, 35.0],  # From Array 1 & 2
            azimuth=[180.0, 90.0],  # From Array 1 & 2
            dc_kwp=[10.0, 5.0],  # From Array 1 & 2
        )
        print("✅ Correct lists passed to OpenMeteoSolarForecast")

        # 7. Verify result aggregation
        # 1000 Watts * 0.25 hours = 250 Wh = 0.25 kWh per slot
        for slot in result["slots"]:
            self.assertEqual(slot["pv_forecast_kwh"], 0.25)

        print("✅ Forecast aggregation result correct (0.25 kWh per slot)")
        print("✅ Multi-array forecast integration verified!")


if __name__ == "__main__":
    unittest.main()
