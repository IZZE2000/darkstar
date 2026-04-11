"""Tests for price forecast API."""

import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
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


class TestPriceForecastStatus(unittest.TestCase):
    """Test price forecast status endpoint returns training_samples_count (Task 1.2)."""

    def setUp(self):
        self.client = TestClient(app)
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")

    def tearDown(self):
        import os

        os.close(self.db_fd)
        Path(self.db_path).unlink()

    def _create_tables(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "CREATE TABLE price_forecasts (id INTEGER PRIMARY KEY, slot_start TEXT, days_ahead INTEGER, spot_p50 REAL)"
        )
        conn.execute(
            "INSERT INTO price_forecasts (slot_start, days_ahead, spot_p50) VALUES ('2026-04-01T00:00:00', 1, 0.5)"
        )
        conn.execute(
            "INSERT INTO price_forecasts (slot_start, days_ahead, spot_p50) VALUES ('2026-04-01T01:00:00', 1, 0.6)"
        )
        conn.commit()
        conn.close()

    @patch("backend.api.routers.price_forecast.get_learning_engine")
    @patch("backend.api.routers.price_forecast._load_config")
    def test_status_includes_training_samples_count(self, mock_load_config, mock_get_engine):
        mock_load_config.return_value = {
            "price_forecast": {"enabled": True, "min_training_samples": 500}
        }
        mock_engine = MagicMock()
        mock_engine.db_path = self.db_path
        mock_get_engine.return_value = mock_engine
        self._create_tables()

        response = self.client.get("/api/price-forecast/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("training_samples_count", data)
        self.assertIsInstance(data["training_samples_count"], int)
        self.assertGreaterEqual(data["training_samples_count"], 0)
        self.assertEqual(data["training_samples_count"], 2)


class TestPriceForecastAccuracy(unittest.TestCase):
    """Test price forecast accuracy endpoint (Task 2.2)."""

    def setUp(self):
        self.client = TestClient(app)
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")

    def tearDown(self):
        import os

        os.close(self.db_fd)
        Path(self.db_path).unlink()

    def _create_tables(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "CREATE TABLE price_forecasts (id INTEGER PRIMARY KEY, slot_start TEXT, days_ahead INTEGER, spot_p50 REAL)"
        )
        conn.execute(
            "CREATE TABLE slot_observations (id INTEGER PRIMARY KEY, slot_start TEXT, export_price_sek_kwh REAL)"
        )
        conn.commit()
        conn.close()

    @patch("backend.api.routers.price_forecast._load_config")
    def test_accuracy_disabled(self, mock_load_config):
        mock_load_config.return_value = {"price_forecast": {"enabled": False}}

        response = self.client.get("/api/price-forecast/accuracy")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["enabled"])
        self.assertIsNone(data["d1_mae"])
        self.assertEqual(data["status"], "disabled")

    @patch("backend.api.routers.price_forecast.get_learning_engine")
    @patch("backend.api.routers.price_forecast._load_config")
    def test_accuracy_insufficient_data(self, mock_load_config, mock_get_engine):
        mock_load_config.return_value = {"price_forecast": {"enabled": True}}
        mock_engine = MagicMock()
        mock_engine.db_path = self.db_path
        mock_get_engine.return_value = mock_engine
        self._create_tables()

        response = self.client.get("/api/price-forecast/accuracy")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["enabled"])
        self.assertIsNone(data["d1_mae"])
        self.assertEqual(data["status"], "insufficient_data")

    @patch("backend.api.routers.price_forecast.get_learning_engine")
    @patch("backend.api.routers.price_forecast._load_config")
    def test_accuracy_with_data(self, mock_load_config, mock_get_engine):
        mock_load_config.return_value = {"price_forecast": {"enabled": True}}
        mock_engine = MagicMock()
        mock_engine.db_path = self.db_path
        mock_get_engine.return_value = mock_engine
        self._create_tables()

        day1 = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%dT00:00:00")
        day2 = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT00:00:00")
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            f"INSERT INTO price_forecasts (slot_start, days_ahead, spot_p50) VALUES ('{day1}', 1, 0.50)"
        )
        conn.execute(
            f"INSERT INTO slot_observations (slot_start, export_price_sek_kwh) VALUES ('{day1}', 0.60)"
        )
        conn.execute(
            f"INSERT INTO price_forecasts (slot_start, days_ahead, spot_p50) VALUES ('{day2}', 1, 0.70)"
        )
        conn.execute(
            f"INSERT INTO slot_observations (slot_start, export_price_sek_kwh) VALUES ('{day2}', 0.80)"
        )
        conn.commit()
        conn.close()

        response = self.client.get("/api/price-forecast/accuracy")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["enabled"])
        self.assertIsNotNone(data["d1_mae"])
        self.assertEqual(data["d1_mae"], 0.1)
        self.assertEqual(data["d1_bias"], -0.1)
        self.assertEqual(data["status"], "ok")


class TestPriceForecastIncludeActuals(unittest.TestCase):
    """Test include_actuals query parameter (Task 3.2)."""

    def setUp(self):
        self.client = TestClient(app)
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")

    def tearDown(self):
        import os

        os.close(self.db_fd)
        Path(self.db_path).unlink()

    def _create_tables(self):
        recent = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT00:00:00")
        issue = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%dT12:00:00")
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "CREATE TABLE price_forecasts (id INTEGER PRIMARY KEY, slot_start TEXT, issue_timestamp TEXT, days_ahead INTEGER, spot_p10 REAL, spot_p50 REAL, spot_p90 REAL, wind_index REAL, temperature_c REAL, cloud_cover REAL, radiation_wm2 REAL)"
        )
        conn.execute(
            "CREATE TABLE slot_observations (id INTEGER PRIMARY KEY, slot_start TEXT, export_price_sek_kwh REAL)"
        )
        conn.execute(
            f"INSERT INTO price_forecasts (slot_start, issue_timestamp, days_ahead, spot_p50) VALUES ('{recent}', '{issue}', 1, 0.5)"
        )
        conn.execute(
            f"INSERT INTO slot_observations (slot_start, export_price_sek_kwh) VALUES ('{recent}', 0.6)"
        )
        conn.commit()
        conn.close()

    @patch("backend.api.routers.price_forecast.get_price_forecasts_from_db")
    @patch("backend.api.routers.price_forecast._price_model_exists")
    @patch("backend.api.routers.price_forecast._load_config")
    @patch("backend.api.routers.price_forecast.get_learning_engine")
    def test_include_actuals_true(
        self, mock_get_engine, mock_load_config, mock_model_exists, mock_get_forecasts
    ):
        mock_load_config.return_value = {"price_forecast": {"enabled": True}}
        mock_model_exists.return_value = True
        mock_engine = MagicMock()
        mock_engine.db_path = self.db_path
        mock_get_engine.return_value = mock_engine
        mock_get_forecasts.return_value = [
            {"slot_start": "2026-04-01T00:00:00", "days_ahead": 1, "spot_p50": 0.5},
        ]
        self._create_tables()

        response = self.client.get("/api/price-forecast?include_actuals=true")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["forecasts"]), 1)
        self.assertIn("actual_spot", data["forecasts"][0])
        self.assertAlmostEqual(data["forecasts"][0]["actual_spot"], 0.6)

    @patch("backend.api.routers.price_forecast.get_price_forecasts_from_db")
    @patch("backend.api.routers.price_forecast._price_model_exists")
    @patch("backend.api.routers.price_forecast._load_config")
    @patch("backend.api.routers.price_forecast.get_learning_engine")
    def test_include_actuals_false(
        self, mock_get_engine, mock_load_config, mock_model_exists, mock_get_forecasts
    ):
        mock_load_config.return_value = {"price_forecast": {"enabled": True}}
        mock_model_exists.return_value = True
        mock_engine = MagicMock()
        mock_engine.db_path = self.db_path
        mock_get_engine.return_value = mock_engine
        mock_get_forecasts.return_value = [
            {"slot_start": "2026-04-01T00:00:00", "days_ahead": 1, "spot_p50": 0.5},
        ]
        self._create_tables()

        response = self.client.get("/api/price-forecast")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["forecasts"]), 1)
        self.assertNotIn("actual_spot", data["forecasts"][0])


if __name__ == "__main__":
    unittest.main()
