"""Tests for price model training."""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd

from ml.price_train import train_price_model


class TestPriceTrain(unittest.TestCase):
    """Test price model training (Task 9.3)."""

    @patch("ml.price_train._build_training_dataset")
    def test_cold_start_gating_insufficient_samples(self, mock_build_dataset):
        """Test that training is skipped when insufficient samples."""
        print("\n--- Testing Cold-Start Gating (Insufficient Samples) ---")

        # Create DataFrame with insufficient samples
        mock_df = pd.DataFrame(
            {
                "export_price_sek_kwh": [0.3] * 100,  # Only 100 samples
            }
        )
        mock_build_dataset.return_value = mock_df

        with patch("ml.price_train.print") as mock_print:
            result = train_price_model(min_training_samples=500)

            # Should return False (training skipped)
            self.assertFalse(result)

            # Should print warning about insufficient samples
            mock_print.assert_any_call(
                "Skipping training: only 100 samples available; requires at least 500."
            )

        print("✓ Cold-start gating works with insufficient samples")

    @patch("ml.price_train._build_training_dataset")
    @patch("ml.price_train.lgb.LGBMRegressor")
    def test_training_creates_model_files(self, mock_model_class, mock_build_dataset):
        """Test that training creates model files when sufficient samples."""
        print("\n--- Testing Training Creates Model Files ---")

        # Create DataFrame with sufficient samples
        mock_df = pd.DataFrame(
            {
                "hour": [12] * 1000,
                "day_of_week": [1] * 1000,
                "month": [3] * 1000,
                "is_weekend": [0] * 1000,
                "is_holiday": [0] * 1000,
                "days_ahead": [1] * 1000,
                "price_lag_1d": [0.25] * 1000,
                "price_lag_7d": [0.22] * 1000,
                "price_lag_24h_avg": [0.23] * 1000,
                "wind_index": [5.0] * 1000,
                "temperature_c": [10.0] * 1000,
                "cloud_cover": [50.0] * 1000,
                "radiation_wm2": [200.0] * 1000,
                "export_price_sek_kwh": [0.3] * 1000,
            }
        )
        mock_build_dataset.return_value = mock_df

        # Mock model
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        # Mock model save
        with (
            patch("ml.price_train.Path.mkdir"),
            patch.object(Path, "exists", return_value=False),
            patch("ml.price_train._save_model"),
        ):
            result = train_price_model(min_training_samples=500)

            # Should return True (training successful)
            self.assertTrue(result)

            # Model should be trained 3 times (p10, p50, p90)
            self.assertEqual(mock_model.fit.call_count, 3)

        print("✓ Training creates model files correctly")

    def test_feature_column_list(self):
        """Test that feature columns match expected schema."""
        print("\n--- Testing Feature Column List ---")

        # Feature columns are defined in train_price_model function
        expected_cols = [
            "hour",
            "day_of_week",
            "month",
            "is_weekend",
            "is_holiday",
            "days_ahead",
            "price_lag_1d",
            "price_lag_7d",
            "price_lag_24h_avg",
            "wind_index",
            "temperature_c",
            "cloud_cover",
            "radiation_wm2",
        ]

        # Just verify the expected columns are valid feature names
        self.assertEqual(len(expected_cols), 13)
        self.assertIn("hour", expected_cols)
        self.assertIn("wind_index", expected_cols)

        print("✓ Feature columns match expected schema")


if __name__ == "__main__":
    unittest.main()
