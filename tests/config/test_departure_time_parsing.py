"""
Tests for _parse_departure_time helper function in executor/config.py

Tests the defensive integer-to-HH:MM converter for YAML 1.1 sexagesimal fallback.
"""

from executor.config import _parse_departure_time


class TestParseDepartureTime:
    """Test the _parse_departure_time function."""

    def test_integer_960_returns_16_00(self):
        """Test: integer 960 (16*60) returns '16:00'"""
        result = _parse_departure_time(960)
        assert result == "16:00"

    def test_integer_1020_returns_17_00(self):
        """Test: integer 1020 (17*60) returns '17:00'"""
        result = _parse_departure_time(1020)
        assert result == "17:00"

    def test_integer_420_returns_07_00(self):
        """Test: integer 420 (7*60) returns '07:00'"""
        result = _parse_departure_time(420)
        assert result == "07:00"

    def test_integer_0_returns_00_00(self):
        """Test: integer 0 returns '00:00' (midnight)"""
        result = _parse_departure_time(0)
        assert result == "00:00"

    def test_integer_1439_returns_23_59(self):
        """Test: integer 1439 (23*60+59) returns '23:59' (last valid minute)"""
        result = _parse_departure_time(1439)
        assert result == "23:59"

    def test_integer_1440_returns_none(self):
        """Test: integer 1440 (out of range) returns None"""
        result = _parse_departure_time(1440)
        assert result is None

    def test_integer_negative_returns_none(self):
        """Test: negative integer returns None"""
        result = _parse_departure_time(-1)
        assert result is None

    def test_none_returns_none(self):
        """Test: None returns None"""
        result = _parse_departure_time(None)
        assert result is None

    def test_empty_string_returns_none(self):
        """Test: empty string returns None"""
        result = _parse_departure_time("")
        assert result is None

    def test_string_16_00_returns_16_00(self):
        """Test: string '16:00' returns '16:00' (passthrough)"""
        result = _parse_departure_time("16:00")
        assert result == "16:00"

    def test_string_07_00_returns_07_00(self):
        """Test: string '07:00' returns '07:00' (passthrough)"""
        result = _parse_departure_time("07:00")
        assert result == "07:00"
