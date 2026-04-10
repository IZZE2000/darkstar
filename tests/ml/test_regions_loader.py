"""Tests for regions.json loading."""

import unittest
from unittest.mock import mock_open, patch

from ml.weather import load_regions_config


class TestRegionsLoader(unittest.TestCase):
    """Test regions.json loading (Task 9.6)."""

    def test_se1_se4_loading(self):
        """Test that all SE1-SE4 price areas are loaded."""
        print("\n--- Testing SE1-SE4 Loading ---")

        # Load actual regions.json
        regions = load_regions_config("ml/regions.json")

        # Verify all expected price areas exist
        expected_areas = ["SE1", "SE2", "SE3", "SE4"]
        for area in expected_areas:
            self.assertIn(area, regions, f"Missing price area: {area}")

        # Verify each area has coordinates
        for area in expected_areas:
            self.assertIsInstance(regions[area], dict)
            self.assertGreater(len(regions[area]), 0, f"{area} has no coordinates")

        print("✓ All SE1-SE4 price areas loaded correctly")

    def test_coordinate_structure(self):
        """Test that coordinate entries have required fields."""
        print("\n--- Testing Coordinate Structure ---")

        regions = load_regions_config("ml/regions.json")

        for area, coords in regions.items():
            for coord_key, coord_data in coords.items():
                self.assertIn("lat", coord_data, f"{area}/{coord_key} missing lat")
                self.assertIn("lon", coord_data, f"{area}/{coord_key} missing lon")

                # Verify lat/lon are valid numbers
                lat = coord_data["lat"]
                lon = coord_data["lon"]
                self.assertIsInstance(lat, (int, float))
                self.assertIsInstance(lon, (int, float))
                self.assertTrue(-90 <= lat <= 90, f"Invalid latitude: {lat}")
                self.assertTrue(-180 <= lon <= 180, f"Invalid longitude: {lon}")

        print("✓ Coordinate structure valid")

    def test_multiple_coordinates_per_area(self):
        """Test that each price area has multiple coordinates."""
        print("\n--- Testing Multiple Coordinates Per Area ---")

        regions = load_regions_config("ml/regions.json")

        for area in ["SE1", "SE2", "SE3", "SE4"]:
            coord_count = len(regions[area])
            self.assertGreaterEqual(
                coord_count, 2, f"{area} should have at least 2 coordinates for regional averaging"
            )

        print("✓ Multiple coordinates per area confirmed")

    @patch(
        "pathlib.Path.open",
        new_callable=mock_open,
        read_data='{"SE4": {"local": {"lat": 59.3, "lon": 18.1}}}',
    )
    def test_unknown_area_fallback(self, mock_file):
        """Test that unknown area returns empty dict."""
        print("\n--- Testing Unknown Area Fallback ---")

        regions = load_regions_config("ml/regions.json")

        # Known area should exist
        self.assertIn("SE4", regions)

        # Unknown area should not exist
        self.assertNotIn("DK1", regions)
        self.assertNotIn("NO1", regions)

        print("✓ Unknown areas handled correctly")

    def test_file_not_found_returns_empty(self):
        """Test that missing file returns empty dict."""
        print("\n--- Testing File Not Found Returns Empty ---")

        regions = load_regions_config("nonexistent_file.json")

        self.assertEqual(regions, {})

        print("✓ Missing file returns empty dict")


if __name__ == "__main__":
    unittest.main()
