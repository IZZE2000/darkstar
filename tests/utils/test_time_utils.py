"""Tests for DST-safe time utility functions."""

import pandas as pd
import pytz

from utils.time_utils import dst_safe_date_range, dst_safe_localize


class TestDstSafeDateRange:
    """Test cases for dst_safe_date_range function."""

    def test_spring_forward_stockholm(self):
        """Test spring-forward DST transition in Europe/Stockholm.

        On 2026-03-29, clocks spring forward from 02:00 to 03:00.
        A 00:00 to 06:00 range should have 20 slots (not 24).
        """
        tz = pytz.timezone("Europe/Stockholm")
        start = pd.Timestamp("2026-03-29 00:00:00")
        end = pd.Timestamp("2026-03-29 06:00:00")

        result = dst_safe_date_range(start=start, end=end, freq="15min", tz=tz, inclusive="left")

        # Should have 20 slots (00:00-02:00 = 8 slots, 03:00-06:00 = 12 slots)
        assert len(result) == 20

        # Verify no timestamps exist between 02:00 and 03:00
        for ts in result:
            assert ts.hour != 2, f"Found timestamp in non-existent hour: {ts}"

        # Verify the gap is handled correctly - should go from 01:45 to 03:00
        timestamps = list(result)
        # Find the transition point
        for i, ts in enumerate(timestamps[:-1]):
            if ts.hour == 1 and ts.minute == 45:
                next_ts = timestamps[i + 1]
                assert next_ts.hour == 3 and next_ts.minute == 0, (
                    f"Expected 03:00 after 01:45, got {next_ts}"
                )

    def test_fall_back_stockholm(self):
        """Test fall-back DST transition in Europe/Stockholm.

        On 2026-10-25, clocks fall back from 03:00 to 02:00.
        A 00:00 to 06:00 range should have 28 slots (not 24).
        """
        tz = pytz.timezone("Europe/Stockholm")
        start = pd.Timestamp("2026-10-25 00:00:00")
        end = pd.Timestamp("2026-10-25 06:00:00")

        result = dst_safe_date_range(start=start, end=end, freq="15min", tz=tz, inclusive="left")

        # Should have 28 slots (00:00-06:00 with duplicated 02:00-03:00 hour)
        assert len(result) == 28

    def test_normal_day_matches_standard_date_range(self):
        """Test that on normal days (no DST transition), results match pd.date_range."""
        tz = pytz.timezone("Europe/Stockholm")
        start = pd.Timestamp("2026-06-15 00:00:00")
        end = pd.Timestamp("2026-06-15 06:00:00")

        # Our DST-safe function
        result_safe = dst_safe_date_range(
            start=start, end=end, freq="15min", tz=tz, inclusive="left"
        )

        # Standard pandas function
        start_local = tz.localize(start)
        end_local = tz.localize(end)
        result_standard = pd.date_range(
            start=start_local, end=end_local, freq="15min", tz=tz, inclusive="left"
        )

        # Results should be identical on normal days
        assert len(result_safe) == len(result_standard)
        for i, (ts_safe, ts_std) in enumerate(zip(result_safe, result_standard, strict=True)):
            assert ts_safe == ts_std, f"Mismatch at index {i}: {ts_safe} != {ts_std}"


class TestDstSafeLocalize:
    """Test cases for dst_safe_localize function."""

    def test_localize_series_spring_forward(self):
        """Test localizing a Series containing spring-forward ambiguous time.

        2026-03-29 02:30:00 doesn't exist in Europe/Stockholm due to DST.
        Should shift forward to 03:00 without error.
        """
        tz = pytz.timezone("Europe/Stockholm")

        # Create a Series with a non-existent time
        timestamps = pd.to_datetime(
            ["2026-03-29 01:30:00", "2026-03-29 02:30:00", "2026-03-29 03:30:00"]
        )
        series = pd.Series(timestamps)

        # Should not raise an exception
        result = dst_safe_localize(series, tz)

        # The non-existent 02:30 should be shifted to 03:00
        assert result.iloc[1].hour == 3
        assert result.iloc[1].minute == 0

    def test_localize_series_fall_back(self):
        """Test localizing a Series containing fall-back ambiguous time.

        2026-10-25 02:30:00 occurs twice in Europe/Stockholm due to DST.
        Should localize without error using ambiguous='infer'.
        """
        tz = pytz.timezone("Europe/Stockholm")

        # Create a Series with an ambiguous time
        timestamps = pd.to_datetime(
            ["2026-10-25 01:30:00", "2026-10-25 02:30:00", "2026-10-25 03:30:00"]
        )
        series = pd.Series(timestamps)

        # Should not raise an exception
        result = dst_safe_localize(series, tz)

        # All timestamps should be localized
        assert result.dt.tz is not None
        assert len(result) == 3

    def test_localize_datetime_index(self):
        """Test localizing a DatetimeIndex."""
        tz = pytz.timezone("Europe/Stockholm")

        # Create a DatetimeIndex with a non-existent time
        timestamps = pd.to_datetime(
            ["2026-03-29 01:30:00", "2026-03-29 02:30:00", "2026-03-29 03:30:00"]
        )

        # Should not raise an exception
        result = dst_safe_localize(timestamps, tz)

        # The non-existent 02:30 should be shifted to 03:00
        assert result[1].hour == 3
        assert result[1].minute == 0

    def test_localize_single_datetime(self):
        """Test localizing a single datetime object."""
        tz = pytz.timezone("Europe/Stockholm")

        # Test non-existent time
        dt = pd.Timestamp("2026-03-29 02:30:00").to_pydatetime()
        result = dst_safe_localize(dt, tz)

        # Should be localized (with is_dst=True fallback)
        assert result.tzinfo is not None
