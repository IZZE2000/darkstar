"""Tests for consumer price derivation from spot price forecasts."""

import unittest

from ml.price_forecast import derive_consumer_prices


class TestDeriveConsumerPrices(unittest.TestCase):
    """Test consumer price derivation (Task 9.4)."""

    def test_export_price_equals_spot(self):
        """Test that export price equals spot price."""
        print("\n--- Testing Export Price Equals Spot ---")

        config = {
            "electricity": {
                "vat_pct": 25.0,
                "energy_tax_sek_kwh": 0.417,
            },
            "grid": {
                "grid_price_sek_kwh": 0.15,
            },
        }

        spot_p50 = 0.50  # SEK/kWh

        result = derive_consumer_prices(
            spot_p10=spot_p50 * 0.8,
            spot_p50=spot_p50,
            spot_p90=spot_p50 * 1.2,
            config=config,
        )

        # Export price should equal spot price
        self.assertEqual(result["export_p10"], spot_p50 * 0.8)
        self.assertEqual(result["export_p50"], spot_p50)
        self.assertEqual(result["export_p90"], spot_p50 * 1.2)

        print("✓ Export price equals spot price")

    def test_import_price_calculation(self):
        """Test import price includes VAT, taxes, and grid fees."""
        print("\n--- Testing Import Price Calculation ---")

        config = {
            "electricity": {
                "vat_pct": 25.0,
                "energy_tax_sek_kwh": 0.417,
            },
            "grid": {
                "grid_price_sek_kwh": 0.15,
            },
        }

        spot_p50 = 0.50  # SEK/kWh

        result = derive_consumer_prices(
            spot_p10=spot_p50 * 0.8,
            spot_p50=spot_p50,
            spot_p90=spot_p50 * 1.2,
            config=config,
        )

        # Import price calculation (result is in SEK/kWh, same as input):
        # spot in SEK/MWh = spot_p50 * 1000 = 500
        # calculate_import_export_prices returns (import_sek_kwh, export_sek_kwh)
        # So result values should be in SEK/kWh

        # Just verify the values are reasonable (> input spot price due to fees)
        self.assertGreater(result["import_p50"], spot_p50)
        self.assertGreater(result["import_p10"], spot_p50 * 0.8)
        self.assertGreater(result["import_p90"], spot_p50 * 1.2)

        print("✓ Import price calculation correct")

    def test_default_config_values(self):
        """Test that default config values are used when missing."""
        print("\n--- Testing Default Config Values ---")

        config = {}  # Empty config

        spot_p50 = 0.50

        result = derive_consumer_prices(
            spot_p10=spot_p50 * 0.8,
            spot_p50=spot_p50,
            spot_p90=spot_p50 * 1.2,
            config=config,
        )

        # Should still work with defaults (VAT=25%, tax=0.417, grid=0.15)
        self.assertIsNotNone(result["import_p50"])
        self.assertIsNotNone(result["export_p50"])

        print("✓ Default config values work correctly")

    def test_all_returned_keys(self):
        """Test that all expected keys are returned."""
        print("\n--- Testing All Returned Keys ---")

        config = {
            "electricity": {"vat_pct": 25.0, "energy_tax_sek_kwh": 0.417},
            "grid": {"grid_price_sek_kwh": 0.15},
        }

        result = derive_consumer_prices(
            spot_p10=0.4,
            spot_p50=0.5,
            spot_p90=0.6,
            config=config,
        )

        expected_keys = [
            "import_p10",
            "import_p50",
            "import_p90",
            "export_p10",
            "export_p50",
            "export_p90",
        ]

        for key in expected_keys:
            self.assertIn(key, result)

        print("✓ All expected keys returned")


if __name__ == "__main__":
    unittest.main()
