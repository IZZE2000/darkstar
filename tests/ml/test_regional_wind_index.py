"""Tests for regional wind index computation."""

import unittest
from datetime import datetime

import pandas as pd
import pytz

from ml.weather import compute_regional_wind_index


class TestRegionalWindIndex(unittest.TestCase):
    """Test regional wind index computation (Task 9.2)."""

    def test_single_coordinate(self):
        """Test wind index with single coordinate."""
        print("\n--- Testing Single Coordinate Wind Index ---")

        start = datetime(2026, 3, 15, 0, 0, tzinfo=pytz.UTC)
        index = pd.date_range(start, periods=4, freq="15min")

        regional_weather = {
            "local": pd.DataFrame({"wind_speed_10m": [5.0, 6.0, 7.0, 8.0]}, index=index)
        }

        wind_index = compute_regional_wind_index(regional_weather)

        # Should be identical to single coordinate
        expected = pd.Series([5.0, 6.0, 7.0, 8.0], name="wind_index", index=index)
        pd.testing.assert_series_equal(wind_index, expected)

        print("✓ Single coordinate wind index correct")

    def test_two_coordinates(self):
        """Test wind index averaging with 2 coordinates."""
        print("\n--- Testing Two Coordinate Wind Index ---")

        start = datetime(2026, 3, 15, 0, 0, tzinfo=pytz.UTC)
        index = pd.date_range(start, periods=4, freq="15min")

        regional_weather = {
            "coord1": pd.DataFrame({"wind_speed_10m": [4.0, 5.0, 6.0, 7.0]}, index=index),
            "coord2": pd.DataFrame({"wind_speed_10m": [6.0, 7.0, 8.0, 9.0]}, index=index),
        }

        wind_index = compute_regional_wind_index(regional_weather)

        # Should be arithmetic mean: (4+6)/2=5, (5+7)/2=6, etc.
        expected = pd.Series([5.0, 6.0, 7.0, 8.0], name="wind_index", index=index)
        pd.testing.assert_series_equal(wind_index, expected)

        print("✓ Two coordinate wind index average correct")

    def test_three_coordinates(self):
        """Test wind index averaging with 3 coordinates."""
        print("\n--- Testing Three Coordinate Wind Index ---")

        start = datetime(2026, 3, 15, 0, 0, tzinfo=pytz.UTC)
        index = pd.date_range(start, periods=3, freq="15min")

        regional_weather = {
            "coord1": pd.DataFrame({"wind_speed_10m": [3.0, 6.0, 9.0]}, index=index),
            "coord2": pd.DataFrame({"wind_speed_10m": [6.0, 6.0, 6.0]}, index=index),
            "coord3": pd.DataFrame({"wind_speed_10m": [9.0, 6.0, 3.0]}, index=index),
        }

        wind_index = compute_regional_wind_index(regional_weather)

        # Arithmetic mean: (3+6+9)/3=6, (6+6+6)/3=6, (9+6+3)/3=6
        expected = pd.Series([6.0, 6.0, 6.0], name="wind_index", index=index)
        pd.testing.assert_series_equal(wind_index, expected)

        print("✓ Three coordinate wind index average correct")

    def test_partial_failure_one_empty(self):
        """Test wind index when one coordinate has no data."""
        print("\n--- Testing Partial Failure (One Empty) ---")

        start = datetime(2026, 3, 15, 0, 0, tzinfo=pytz.UTC)
        index = pd.date_range(start, periods=3, freq="15min")

        regional_weather = {
            "coord1": pd.DataFrame({"wind_speed_10m": [5.0, 6.0, 7.0]}, index=index),
            "coord2": pd.DataFrame(),  # Empty
        }

        wind_index = compute_regional_wind_index(regional_weather)

        # Should still work with just coord1
        expected = pd.Series([5.0, 6.0, 7.0], name="wind_index", index=index)
        pd.testing.assert_series_equal(wind_index, expected)

        print("✓ Partial failure handled correctly")

    def test_partial_failure_no_wind_column(self):
        """Test wind index when one coordinate lacks wind speed column."""
        print("\n--- Testing Partial Failure (No Wind Column) ---")

        start = datetime(2026, 3, 15, 0, 0, tzinfo=pytz.UTC)
        index = pd.date_range(start, periods=3, freq="15min")

        regional_weather = {
            "coord1": pd.DataFrame({"wind_speed_10m": [5.0, 6.0, 7.0]}, index=index),
            "coord2": pd.DataFrame(
                {
                    "temperature_2m": [10.0, 11.0, 12.0]  # No wind_speed column
                },
                index=index,
            ),
        }

        wind_index = compute_regional_wind_index(regional_weather)

        # Should still work with just coord1
        expected = pd.Series([5.0, 6.0, 7.0], name="wind_index", index=index)
        pd.testing.assert_series_equal(wind_index, expected)

        print("✓ Missing wind column handled correctly")

    def test_all_empty_returns_empty(self):
        """Test that empty result is returned when all coordinates fail."""
        print("\n--- Testing All Empty Returns Empty ---")

        regional_weather = {
            "coord1": pd.DataFrame(),
            "coord2": pd.DataFrame(),
        }

        wind_index = compute_regional_wind_index(regional_weather)

        self.assertTrue(wind_index.empty)
        self.assertEqual(wind_index.name, "wind_index")

        print("✓ All empty returns empty series correctly")

    def test_alternative_wind_column_names(self):
        """Test detection of alternative wind column names."""
        print("\n--- Testing Alternative Wind Column Names ---")

        start = datetime(2026, 3, 15, 0, 0, tzinfo=pytz.UTC)
        index = pd.date_range(start, periods=3, freq="15min")

        # Test various wind column naming conventions (all contain "wind_speed")
        regional_weather = {
            "coord_wind_speed_10m": pd.DataFrame({"wind_speed_10m": [5.0, 6.0, 7.0]}, index=index),
            "coord_wind_speed_100m": pd.DataFrame(
                {"wind_speed_100m": [6.0, 7.0, 8.0]}, index=index
            ),
        }

        wind_index = compute_regional_wind_index(regional_weather)

        # Should find both wind columns
        expected = pd.Series([5.5, 6.5, 7.5], name="wind_index", index=index)
        pd.testing.assert_series_equal(wind_index, expected)

        print("✓ Alternative wind column names detected correctly")


if __name__ == "__main__":
    unittest.main()
