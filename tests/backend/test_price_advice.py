"""Tests for price advisor rules (Task 6.4 component)."""

import unittest
from unittest.mock import patch

from backend.api.routers.analyst import _get_price_advice, _get_strategy_advice


class TestGetPriceAdvice(unittest.TestCase):
    """Test _get_price_advice() rule engine (Task 6.4)."""

    def test_cheapest_day_ahead_rule(self):
        """Test 'cheapest day ahead' rule fires when 30%+ drop."""
        print("\n--- Testing Cheapest Day Ahead Rule ---")

        daily_outlook = [
            {
                "day_label": "Mon",
                "avg_spot_p50": 0.3,
                "days_ahead": 1,
                "min_hour_p50": 0.2,
                "max_hour_p50": 0.4,
            },
            {
                "day_label": "Tue",
                "avg_spot_p50": 0.5,
                "days_ahead": 2,
                "min_hour_p50": 0.3,
                "max_hour_p50": 0.7,
            },
        ]
        today_avg = 0.5  # 40% drop on Monday

        result = _get_price_advice(daily_outlook, today_avg)

        # Should have cheapest day rule (may also have cheap overnight)
        cheapest_rules = [r for r in result if "drop" in r["message"].lower()]
        self.assertEqual(len(cheapest_rules), 1)
        self.assertEqual(cheapest_rules[0]["category"], "price")
        self.assertIn("Mon", cheapest_rules[0]["message"])
        self.assertIn("40%", cheapest_rules[0]["message"])

        print("✓ Cheapest day ahead rule fires correctly")

    def test_prices_rising_rule(self):
        """Test 'prices rising' rule when D+1-D+3 all higher."""
        print("\n--- Testing Prices Rising Rule ---")

        daily_outlook = [
            {
                "day_label": "Mon",
                "avg_spot_p50": 0.6,
                "days_ahead": 1,
                "min_hour_p50": 0.4,
                "max_hour_p50": 0.8,
            },
            {
                "day_label": "Tue",
                "avg_spot_p50": 0.7,
                "days_ahead": 2,
                "min_hour_p50": 0.5,
                "max_hour_p50": 0.9,
            },
            {
                "day_label": "Wed",
                "avg_spot_p50": 0.8,
                "days_ahead": 3,
                "min_hour_p50": 0.6,
                "max_hour_p50": 1.0,
            },
        ]
        today_avg = 0.5  # All higher than today

        result = _get_price_advice(daily_outlook, today_avg)

        # Should have prices rising rule + cheap overnight rule
        rising_rules = [r for r in result if "rising" in r["message"].lower()]
        self.assertEqual(len(rising_rules), 1)
        self.assertIn("cheapest day", rising_rules[0]["message"].lower())

        print("✓ Prices rising rule fires correctly")

    def test_cheap_overnight_rule(self):
        """Test 'cheap overnight' rule when min is 25%+ below avg."""
        print("\n--- Testing Cheap Overnight Rule ---")

        # min_hour_p50=0.3 should be 40% below avg_spot_p50=0.5
        # 0.3 < 0.5 * 0.75 = 0.375, so condition should be True
        daily_outlook = [
            {
                "day_label": "Mon",
                "avg_spot_p50": 0.5,
                "days_ahead": 1,
                "min_hour_p50": 0.3,
                "max_hour_p50": 0.7,
            },
        ]
        today_avg = 0.5

        result = _get_price_advice(daily_outlook, today_avg)

        # Should detect cheap overnight (0.3 is 40% below 0.5 avg)
        # Note: message says "Tonight" not "overnight"
        overnight_rules = [r for r in result if "tonight" in r["message"].lower()]
        self.assertGreaterEqual(len(overnight_rules), 1)
        self.assertIn("22:00-06:00", overnight_rules[0]["message"])

        print("✓ Cheap overnight rule fires correctly")

    def test_no_advice_when_thresholds_not_met(self):
        """Test no advice when thresholds are not met."""
        print("\n--- Testing No Advice When Thresholds Not Met ---")

        daily_outlook = [
            {
                "day_label": "Mon",
                "avg_spot_p50": 0.48,
                "days_ahead": 1,
                "min_hour_p50": 0.45,
                "max_hour_p50": 0.52,
            },
        ]
        today_avg = 0.5  # Only 4% difference, not 30%

        result = _get_price_advice(daily_outlook, today_avg)

        # Should have no advice (no cheap day, no rising, no cheap overnight)
        self.assertEqual(len(result), 0)

        print("✓ No advice when thresholds not met")

    def test_empty_output_when_no_data(self):
        """Test empty output when daily_outlook is empty."""
        print("\n--- Testing Empty Output ---")

        result = _get_price_advice([], 0.5)

        self.assertEqual(len(result), 0)

        print("✓ Empty output when no data")


class TestStrategyAdviceIntegration(unittest.TestCase):
    """Test integration of price advice into strategy advice (Task 6.6)."""

    @patch("backend.api.routers.analyst.load_yaml")
    @patch("backend.core.price_outlook.get_daily_outlook")
    @patch("backend.core.forecasts.get_forecast_db_path")
    def test_price_advice_appended_to_existing(
        self, mock_get_db_path, mock_get_outlook, mock_load_config
    ):
        """Test price advice is appended to existing advice items."""
        print("\n--- Testing Price Advice Appended to Existing ---")

        # Mock config with price forecast enabled
        mock_load_config.return_value = {
            "price_forecast": {"enabled": True},
            "s_index": {"risk_appetite": 5},  # Will trigger risk advice
        }

        # Mock outlook data that triggers price advice
        mock_get_outlook.return_value = [
            {
                "day_label": "Mon",
                "avg_spot_p50": 0.3,
                "days_ahead": 1,
                "min_hour_p50": 0.2,
                "max_hour_p50": 0.5,
            }
        ]

        result = _get_strategy_advice()

        # Should have both risk advice and price advice
        categories = [item["category"] for item in result["advice"]]

        self.assertIn("risk", categories)  # Existing advice
        self.assertIn("price", categories)  # New price advice

        print("✓ Price advice appended to existing advice")

    @patch("backend.api.routers.analyst.load_yaml")
    def test_existing_advice_unchanged_when_forecast_disabled(self, mock_load_config):
        """Test existing advice unchanged when price forecast disabled."""
        print("\n--- Testing Existing Advice Unchanged When Disabled ---")

        # Mock config with price forecast disabled
        mock_load_config.return_value = {
            "price_forecast": {"enabled": False},
            "s_index": {"risk_appetite": 5},  # Will trigger risk advice
        }

        result = _get_strategy_advice()

        # Should have risk advice but no price advice
        categories = [item["category"] for item in result["advice"]]

        self.assertIn("risk", categories)
        self.assertNotIn("price", categories)

        print("✓ Existing advice unchanged when forecast disabled")


if __name__ == "__main__":
    unittest.main()
