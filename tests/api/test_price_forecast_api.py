"""Tests for price forecast API."""

import unittest
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.routers.price_forecast import router

# Create test app
app = FastAPI()
app.include_router(router)


class TestPriceForecastAPI(unittest.TestCase):
    """Test price forecast API (Task 9.5)."""

    def setUp(self):
        self.client = TestClient(app)

    @patch("backend.api.routers.price_forecast._load_config")
    @patch("backend.api.routers.price_forecast._price_model_exists")
    @patch("backend.api.routers.price_forecast.get_price_forecasts_from_db")
    @patch("backend.api.routers.price_forecast.get_learning_engine")
    def test_enabled_with_model(
        self, mock_get_engine, mock_get_forecasts, mock_model_exists, mock_load_config
    ):
        """Test API returns forecasts when enabled and model exists."""
        print("\n--- Testing API Enabled With Model ---")

        mock_load_config.return_value = {"price_forecast": {"enabled": True}}
        mock_model_exists.return_value = True

        # Mock forecasts
        mock_forecasts = [
            {
                "slot_start": "2026-03-15T00:00:00",
                "days_ahead": 1,
                "spot_p10": 0.4,
                "spot_p50": 0.5,
                "spot_p90": 0.6,
            }
        ]
        mock_get_forecasts.return_value = mock_forecasts

        # Mock engine
        mock_engine = MagicMock()
        mock_engine.db_path = "data/test.db"
        mock_get_engine.return_value = mock_engine

        response = self.client.get("/api/price-forecast")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "enabled")
        self.assertEqual(len(data["forecasts"]), 1)

        print("✓ API returns forecasts when enabled with model")

    @patch("backend.api.routers.price_forecast._load_config")
    def test_disabled(self, mock_load_config):
        """Test API returns disabled status when feature is disabled."""
        print("\n--- Testing API Disabled ---")

        mock_load_config.return_value = {"price_forecast": {"enabled": False}}

        response = self.client.get("/api/price-forecast")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "disabled")
        self.assertIn("disabled", data["message"].lower())

        print("✓ API returns disabled status correctly")

    @patch("backend.api.routers.price_forecast._load_config")
    @patch("backend.api.routers.price_forecast._price_model_exists")
    def test_no_model(self, mock_model_exists, mock_load_config):
        """Test API returns no-model status when model doesn't exist."""
        print("\n--- Testing API No Model ---")

        mock_load_config.return_value = {"price_forecast": {"enabled": True}}
        mock_model_exists.return_value = False

        response = self.client.get("/api/price-forecast")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "no_model")
        self.assertIn("not yet trained", data["message"].lower())

        print("✓ API returns no-model status correctly")

    @patch("backend.api.routers.price_forecast._load_config")
    def test_config_missing_section(self, mock_load_config):
        """Test API handles missing price_forecast config section."""
        print("\n--- Testing API Missing Config Section ---")

        mock_load_config.return_value = {}  # No price_forecast section

        response = self.client.get("/api/price-forecast")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "disabled")

        print("✓ API handles missing config section correctly")

    @patch("backend.api.routers.price_forecast._load_config")
    @patch("backend.core.price_outlook.get_daily_outlook")
    @patch("backend.core.price_outlook.get_trailing_avg")
    def test_outlook_endpoint_enabled_with_data(
        self, mock_get_trailing, mock_get_outlook, mock_load_config
    ):
        """Test outlook endpoint returns correct shape when enabled with data."""
        print("\n--- Testing Outlook Endpoint Enabled With Data ---")

        mock_load_config.return_value = {"price_forecast": {"enabled": True}}
        mock_get_trailing.return_value = 0.5
        mock_get_outlook.return_value = [
            {
                "date": "2026-03-31",
                "day_label": "Mon",
                "days_ahead": 1,
                "avg_spot_p50": 0.45,
                "avg_spot_p10": 0.32,
                "avg_spot_p90": 0.58,
                "min_hour_p50": 0.22,
                "max_hour_p50": 0.78,
            }
        ]

        response = self.client.get("/api/price-forecast/outlook")

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data["enabled"])
        self.assertEqual(data["status"], "ok")
        self.assertEqual(len(data["days"]), 1)
        self.assertEqual(data["reference_avg"], 0.5)

        # Check day fields
        day = data["days"][0]
        self.assertEqual(day["date"], "2026-03-31")
        self.assertEqual(day["day_label"], "Mon")
        self.assertEqual(day["days_ahead"], 1)
        self.assertIn("level", day)
        self.assertIn("confidence", day)

        print("✓ Outlook endpoint returns correct shape when enabled with data")

    @patch("backend.api.routers.price_forecast._load_config")
    def test_outlook_endpoint_disabled(self, mock_load_config):
        """Test outlook endpoint returns disabled response."""
        print("\n--- Testing Outlook Endpoint Disabled ---")

        mock_load_config.return_value = {"price_forecast": {"enabled": False}}

        response = self.client.get("/api/price-forecast/outlook")

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertFalse(data["enabled"])
        self.assertEqual(data["status"], "disabled")
        self.assertEqual(len(data["days"]), 0)

        print("✓ Outlook endpoint returns disabled response")

    @patch("backend.api.routers.price_forecast._load_config")
    @patch("backend.core.price_outlook.get_daily_outlook")
    @patch("backend.core.price_outlook.get_trailing_avg")
    def test_outlook_endpoint_no_data(self, mock_get_trailing, mock_get_outlook, mock_load_config):
        """Test outlook endpoint returns no_data response."""
        print("\n--- Testing Outlook Endpoint No Data ---")

        mock_load_config.return_value = {"price_forecast": {"enabled": True}}
        mock_get_trailing.return_value = 0.5
        mock_get_outlook.return_value = []  # Empty data

        response = self.client.get("/api/price-forecast/outlook")

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data["enabled"])
        self.assertEqual(data["status"], "no_data")
        self.assertEqual(len(data["days"]), 0)

        print("✓ Outlook endpoint returns no_data response")


if __name__ == "__main__":
    unittest.main()
