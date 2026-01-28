from datetime import datetime, timedelta

import pandas as pd
import pytest

from planner.strategy.terminal_value import TerminalValueSystem


@pytest.fixture
def basic_config():
    return {"s_index": {"risk_appetite": 3}}  # Neutral risk


def test_tvs_tomorrow_peaks(basic_config):
    """Test TVS logic when tomorrow's prices are available (peaks detected)."""
    tvs = TerminalValueSystem(basic_config)

    # Mock current time: Monday 10:00
    now = datetime(2025, 1, 27, 10, 0, 0)  # Monday

    # Create DF covering Today + Tomorrow
    # Tomorrow is Tuesday
    timestamps = pd.date_range(start=now, periods=48, freq="1h")
    df = pd.DataFrame(index=timestamps)
    df["import_price_sek_kwh"] = 0.5  # Base price

    # Set Morning Peak for Tomorrow (06-09): 1.0 SEK
    tomorrow_start = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    morning_idx = [t for t in timestamps if t >= tomorrow_start and 6 <= t.hour < 9]
    df.loc[morning_idx, "import_price_sek_kwh"] = 1.0

    # Set Evening Peak for Tomorrow (17-21): 2.0 SEK
    evening_idx = [t for t in timestamps if t >= tomorrow_start and 17 <= t.hour < 21]
    df.loc[evening_idx, "import_price_sek_kwh"] = 2.0

    # Logic should pick max(morning_avg, evening_avg) = 2.0
    val, debug = tvs.calculate_terminal_value(df, now)

    assert val == 2.0
    assert debug["method"] == "tomorrow_peaks"
    assert debug["base_market_value"] == 2.0


def test_tvs_tomorrow_no_peaks(basic_config):
    """Test TVS logic when tomorrow has data but no peaks (constant price)."""
    tvs = TerminalValueSystem(basic_config)
    now = datetime(2025, 1, 27, 10, 0, 0)

    timestamps = pd.date_range(start=now, periods=48, freq="1h")
    df = pd.DataFrame(index=timestamps)
    df["import_price_sek_kwh"] = 0.5  # Constant

    val, debug = tvs.calculate_terminal_value(df, now)

    # Max peak is same as mean
    assert val == 0.5
    assert debug["method"] == "tomorrow_peaks"


def test_tvs_today_only(basic_config):
    """Test TVS logic when only today's prices are available."""
    tvs = TerminalValueSystem(basic_config)
    now = datetime(2025, 1, 27, 10, 0, 0)  # Monday

    # Only 10 hours left today
    timestamps = pd.date_range(start=now, periods=10, freq="1h")
    df = pd.DataFrame(index=timestamps)
    df["import_price_sek_kwh"] = 0.8

    val, debug = tvs.calculate_terminal_value(df, now)

    assert val == 0.8
    assert "today_projection" in debug["method"]


def test_tvs_weekend_adjustment(basic_config):
    """Test weekend adjustment (Today is Friday -> Tomorrow is Saturday)."""
    tvs = TerminalValueSystem(basic_config)
    now = datetime(2025, 1, 24, 10, 0, 0)  # Friday

    # Only today data available
    timestamps = pd.date_range(start=now, periods=10, freq="1h")
    df = pd.DataFrame(index=timestamps)
    df["import_price_sek_kwh"] = 1.0

    val, debug = tvs.calculate_terminal_value(df, now)

    # Expected: 1.0 * 0.95 (Weekend adj) * 1.0 (Risk)
    assert val == 0.95
    assert "weekend_adj" in debug["method"]


def test_tvs_risk_multiplier():
    """Test risk multiplier application."""
    # Risk 1 (Safety) -> 1.30x
    config = {"s_index": {"risk_appetite": 1}}
    tvs = TerminalValueSystem(config)
    now = datetime(2025, 1, 27, 10, 0, 0)

    timestamps = pd.date_range(start=now, periods=48, freq="1h")
    df = pd.DataFrame(index=timestamps)
    df["import_price_sek_kwh"] = 1.0

    val, debug = tvs.calculate_terminal_value(df, now)

    # Base 1.0 * Risk 1.30
    assert val == 1.3
    assert debug["risk_multiplier"] == 1.3
