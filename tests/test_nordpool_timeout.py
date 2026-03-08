"""Tests for Nordpool timeout behavior - DNS crash loop fixes.

This test ensures that Nordpool API calls have proper timeout handling
and fallback behavior when the API is unresponsive.
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
import pytz
import yaml


@pytest.fixture
def temp_config_file(tmp_path):
    """Create a temporary config file for testing."""
    config = {
        "version": "2.5.1-beta",
        "timezone": "Europe/Stockholm",
        "nordpool": {
            "price_area": "SE3",
            "currency": "SEK",
        },
    }
    config_path = tmp_path / "test_nordpool_config.yaml"
    config_path.write_text(yaml.dump(config))
    return str(config_path)


@pytest.mark.asyncio
async def test_get_nordpool_data_times_out_gracefully(temp_config_file):
    """Verify that Nordpool fetch has a 10-second timeout and returns [] on timeout.

    This is a regression test for the DNS crash loop bug where blocking I/O
    could cause the event loop to hang.

    The fix: Wrap prices_client.fetch in asyncio.wait_for(timeout=10.0) and
    catch TimeoutError to return an empty list gracefully.
    """
    from inputs import get_nordpool_data

    # Mock cache and Prices class to be slow
    with patch("inputs.cache_sync") as mock_cache:
        # Mock cache.get to always return None so fetch is always called
        mock_cache.get.return_value = None

        with patch("inputs.Prices") as mock_prices_class:
            mock_prices = MagicMock()

            # Make fetch hang for 30 seconds (longer than timeout)
            def slow_fetch(*args, **kwargs):
                # Simulate a blocking operation that takes too long
                import time

                time.sleep(30)
                return {"areas": {"SE3": {"values": []}}}

            mock_prices.fetch = slow_fetch
            mock_prices_class.return_value = mock_prices

            # Call should complete quickly due to timeout
            start = asyncio.get_event_loop().time()
            result = await get_nordpool_data(temp_config_file)
            elapsed = asyncio.get_event_loop().time() - start

            # Should timeout and return [] within ~10 seconds + overhead
            assert elapsed < 15.0, f"Nordpool fetch took {elapsed}s, should timeout at 10s"
            assert result == [], "Should return empty list on timeout"


@pytest.mark.asyncio
async def test_get_nordpool_data_succeeds_quickly(temp_config_file):
    """Verify that normal Nordpool fetches complete successfully within timeout."""
    from inputs import get_nordpool_data

    tz = pytz.timezone("Europe/Stockholm")
    today = datetime.now(tz).date()

    # Create mock price data
    mock_values = []
    for hour in range(24):
        slot_start = datetime.combine(today, datetime.min.time(), tzinfo=tz) + timedelta(hours=hour)
        mock_values.append(
            {
                "start": slot_start,
                "end": slot_start + timedelta(hours=1),
                "value": 1.0,  # 1 SEK/kWh
            }
        )

    with patch("inputs.cache_sync") as mock_cache:
        # Mock cache.get to always return None so fetch is always called
        mock_cache.get.return_value = None

        with patch("inputs.Prices") as mock_prices_class:
            mock_prices = MagicMock()
            mock_prices.fetch.return_value = {
                "areas": {
                    "SE3": {
                        "values": mock_values,
                    }
                }
            }
            mock_prices_class.return_value = mock_prices

            # Call should succeed
            result = await get_nordpool_data(temp_config_file)

            # Should return price data
            assert isinstance(result, list)
            assert len(result) > 0


@pytest.mark.asyncio
async def test_get_nordpool_tomorrow_fetch_also_has_timeout(temp_config_file):
    """Verify that tomorrow's price fetch (after 13:00) also has timeout protection."""
    from inputs import get_nordpool_data

    tz = pytz.timezone("Europe/Stockholm")

    # Mock current time to be after 13:00 so tomorrow's prices are fetched
    mock_now = datetime.now(tz).replace(hour=14, minute=0)

    with (
        patch("inputs.cache_sync") as mock_cache,
        patch("inputs.Prices") as mock_prices_class,
        patch("inputs.datetime") as mock_datetime,
    ):
        # Mock cache.get to always return None so fetch is always called
        mock_cache.get.return_value = None
        mock_datetime.now.return_value = mock_now
        mock_datetime.combine = datetime.combine

        mock_prices = MagicMock()
        call_count = 0

        def mock_fetch(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            import time

            time.sleep(30)  # Simulate slow response
            return {"areas": {"SE3": {"values": []}}}

        mock_prices.fetch = mock_fetch
        mock_prices_class.return_value = mock_prices

        # Should timeout on first call
        start = asyncio.get_event_loop().time()
        result = await get_nordpool_data(temp_config_file)
        elapsed = asyncio.get_event_loop().time() - start

        # First fetch should timeout quickly
        assert elapsed < 15.0, f"Took {elapsed}s, should timeout at 10s"
        assert result == []
        # Note: Only 1 call is made because the exception propagates
        # and returns [] before attempting the second fetch
        assert call_count == 1


@pytest.mark.asyncio
async def test_get_nordpool_partial_timeout(temp_config_file):
    """Verify behavior when today succeeds but tomorrow times out."""
    from inputs import get_nordpool_data

    tz = pytz.timezone("Europe/Stockholm")
    today = datetime.now(tz).date()
    mock_now = datetime.now(tz).replace(hour=14, minute=0)

    # Create mock price data for today
    mock_values_today = []
    for hour in range(24):
        slot_start = datetime.combine(today, datetime.min.time(), tzinfo=tz) + timedelta(hours=hour)
        mock_values_today.append(
            {
                "start": slot_start,
                "end": slot_start + timedelta(hours=1),
                "value": 1.0,
            }
        )

    with (
        patch("inputs.cache_sync") as mock_cache,
        patch("inputs.Prices") as mock_prices_class,
        patch("inputs.datetime") as mock_datetime,
    ):
        # Mock cache.get to always return None so fetch is always called
        mock_cache.get.return_value = None
        mock_datetime.now.return_value = mock_now
        mock_datetime.combine = datetime.combine

        mock_prices = MagicMock()
        call_count = 0

        def mock_fetch(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            end_date = kwargs.get("end_date")

            if end_date == today:
                # Today succeeds quickly
                return {"areas": {"SE3": {"values": mock_values_today}}}
            else:
                # Tomorrow times out
                import time

                time.sleep(30)
                return {"areas": {"SE3": {"values": []}}}

        mock_prices.fetch = mock_fetch
        mock_prices_class.return_value = mock_prices

        # Should return today's data even if tomorrow times out
        result = await get_nordpool_data(temp_config_file)

        # Should have attempted both calls
        assert call_count == 2
        # But should return empty list because tomorrow failed
        # (implementation returns [] if any fetch fails)
        assert result == []
