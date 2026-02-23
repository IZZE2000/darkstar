import unittest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytz

from backend.learning import LearningEngine
from ml.forward import generate_forward_slots


class TestAuroraForward(unittest.IsolatedAsyncioTestCase):
    @patch("ml.forward.get_learning_engine")
    @patch("ml.forward._load_models")
    @patch("ml.forward.get_weather_series")
    @patch("ml.forward.get_vacation_mode_series")
    @patch("ml.forward.get_alarm_armed_series")
    @patch("backend.astro.SunCalculator")
    @patch("ml.forward._determine_graduation_level")
    async def test_forward_pass_multi_array(
        self,
        mock_grad_level,
        mock_sun,
        mock_alarm,
        mock_vacation,
        mock_weather,
        mock_models,
        mock_get_engine,
    ):
        print("\n--- Testing Aurora Forward Pass with Multi-Array ---")

        # 1. Mock graduation level
        mock_grad_level.return_value = MagicMock(level=2)

        # 2. Mock LearningEngine
        mock_engine = MagicMock(spec=LearningEngine)
        mock_engine.store_forecasts = AsyncMock()
        mock_engine.timezone = pytz.UTC
        mock_engine.db_path = "fake_db.db"

        # 2. Mock SunCalculator
        mock_sun_instance = MagicMock()
        mock_sun_instance.is_sun_up.return_value = True
        mock_sun.return_value = mock_sun_instance
        mock_engine.config = {
            "timezone": "UTC",
            "system": {
                "location": {"latitude": 59.3, "longitude": 18.1},
                "solar_arrays": [{"kwp": 10.0}, {"kwp": 5.0}],
            },
        }
        mock_engine.store_forecasts = AsyncMock()
        mock_get_engine.return_value = mock_engine

        # 2. Mock Models (empty to trigger fallback)
        mock_models.return_value = {}

        # 3. Mock Weather data
        # Get start time that forward pass will actually use (current slot alignment)
        now = datetime.now(pytz.UTC)
        minutes = (now.minute // 15) * 15
        slot_start = now.replace(minute=minutes, second=0, microsecond=0)

        mock_weather.return_value = pd.DataFrame(
            {
                "temp_c": [20.0] * 8,
                "cloud_cover_pct": [10.0] * 8,
                "shortwave_radiation_w_m2": [800.0] * 8,
            },
            index=pd.date_range(slot_start, periods=8, freq="15min", tz="UTC"),
        )

        # 4. Mock Context flags
        mock_vacation.return_value = pd.Series(0.0, index=mock_weather.return_value.index)
        mock_alarm.return_value = pd.Series(0.0, index=mock_weather.return_value.index)

        # 5. Run forward pass (short horizon)
        await generate_forward_slots(horizon_hours=2, forecast_version="test")

        # 6. Verify total PV capacity used in fallback
        # In radiation fallback: pv_kw = (rad / 1000.0) * pv_capacity_kw * efficiency
        # rad = 800.0, pv_capacity_kw = 15.0, efficiency = 0.15
        # pv_kw = 0.8 * 15.0 * 0.15 = 1.8 kW
        # pv_kwh (15 min) = 1.8 * 0.25 = 0.45 kWh

        args, _ = mock_engine.store_forecasts.call_args
        forecasts = args[0]

        self.assertGreater(len(forecasts), 0)
        # Check p50 PV forecast for first slot
        first_pv = forecasts[0]["pv_forecast_kwh"]
        # Allow small floating point difference
        self.assertAlmostEqual(first_pv, 0.45, places=2)

        print("✅ Aurora forward pass used total capacity: 15.0 kWp")
        print(f"✅ Calculated PV forecast: {first_pv} kWh (Expected ~0.45)")
        print("✅ Aurora forward pass multi-array integration verified!")


if __name__ == "__main__":
    unittest.main()
