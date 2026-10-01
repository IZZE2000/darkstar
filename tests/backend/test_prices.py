from datetime import datetime, timedelta

import pytest
import pytz

from backend.core.prices import _process_nordpool_data

local_tz = pytz.timezone("Europe/Stockholm")


def _make_entry(hour: int, value: float, base_date: datetime | None = None) -> dict:
    if base_date is None:
        base_date = datetime(2026, 4, 28)
    start = local_tz.localize(base_date.replace(hour=hour, minute=0, second=0, microsecond=0))
    end = start + timedelta(hours=1)
    return {"start": start, "end": end, "value": value}


def test_dedup_keeps_nordpool_over_fallback():
    """Duplicate start_time values: first occurrence (Nordpool) wins."""
    nordpool_entry = _make_entry(10, 500.0)
    fallback_entry = _make_entry(10, 300.0)

    all_entries = [nordpool_entry, fallback_entry, _make_entry(11, 600.0)]

    result = _process_nordpool_data(all_entries, {"timezone": "Europe/Stockholm"})

    assert len(result) == 2

    slot_10 = [s for s in result if s["start_time"].hour == 10]
    assert len(slot_10) == 1
    assert slot_10[0]["export_price_sek_kwh"] == pytest.approx(500.0 / 1000.0)


# --- Last-good fallback when Nordpool is unreachable ---------------------------

from unittest.mock import AsyncMock, patch  # noqa: E402

import yaml  # noqa: E402

import backend.core.prices as prices_mod  # noqa: E402
from backend.core.cache import cache_sync  # noqa: E402
from backend.core.prices import get_nordpool_data  # noqa: E402


def _day_values(day: datetime, value: float) -> list[dict]:
    return [_make_entry(h, value + h, base_date=day) for h in range(24)]


def _raw(values: list[dict]) -> dict:
    return {"areas": {"SE3": {"values": values}}}


@pytest.fixture
def price_config(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "timezone": "Europe/Stockholm",
                "nordpool": {"price_area": "SE3", "currency": "SEK", "resolution_minutes": 60},
            }
        )
    )
    return str(path)


@pytest.fixture(autouse=True)
def _clear_price_cache():
    cache_sync.invalidate("nordpool_data")
    cache_sync.invalidate(prices_mod._LAST_GOOD_CACHE_KEY)
    yield
    cache_sync.invalidate("nordpool_data")
    cache_sync.invalidate(prices_mod._LAST_GOOD_CACHE_KEY)


def _freeze_now(monkeypatch, frozen: datetime) -> None:
    class _FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):  # type: ignore[override]
            return frozen.astimezone(tz) if tz else frozen.replace(tzinfo=None)

    monkeypatch.setattr(prices_mod, "datetime", _FrozenDatetime)


async def _prime_cache_afternoon(monkeypatch, price_config) -> None:
    """Successful 14:00 fetch on 2026-09-30: today + tomorrow (2026-10-01)."""
    today = datetime(2026, 9, 30)
    tomorrow = datetime(2026, 10, 1)
    _freeze_now(monkeypatch, local_tz.localize(datetime(2026, 9, 30, 14, 0)))

    def fetch(end_date, areas, resolution):
        return _raw(_day_values(today, 1000.0) + _day_values(tomorrow, 2000.0))

    with patch.object(prices_mod.Prices, "fetch", side_effect=fetch):
        result = await get_nordpool_data(price_config)
    assert len(result) == 48


@pytest.mark.asyncio
async def test_nordpool_failure_after_midnight_serves_last_good_prices(monkeypatch, price_config):
    """Regression 2026-10-01: Nordpool 502 at 00:00 must not leave the planner without
    today's prices, which were already fetched as 'tomorrow' the afternoon before."""
    await _prime_cache_afternoon(monkeypatch, price_config)

    _freeze_now(monkeypatch, local_tz.localize(datetime(2026, 10, 1, 0, 0, 36)))
    with (
        patch.object(prices_mod.Prices, "fetch", side_effect=RuntimeError("502 Bad Gateway")),
        patch("ml.price_forecast.get_d1_price_forecast_fallback", new=AsyncMock(return_value=[])),
    ):
        result = await get_nordpool_data(price_config)

    assert len(result) == 24
    assert result[0]["start_time"] == local_tz.localize(datetime(2026, 10, 1, 0, 0))
    assert result[-1]["end_time"] == local_tz.localize(datetime(2026, 10, 2, 0, 0))
    assert result[0]["export_price_sek_kwh"] == pytest.approx(2.0)


@pytest.mark.asyncio
async def test_nordpool_failure_with_exhausted_last_good_returns_empty(monkeypatch, price_config):
    """Cached prices that no longer cover 'now' must not be served."""
    await _prime_cache_afternoon(monkeypatch, price_config)

    _freeze_now(monkeypatch, local_tz.localize(datetime(2026, 10, 2, 0, 30)))
    with (
        patch.object(prices_mod.Prices, "fetch", side_effect=RuntimeError("502 Bad Gateway")),
        patch("ml.price_forecast.get_d1_price_forecast_fallback", new=AsyncMock(return_value=[])),
    ):
        result = await get_nordpool_data(price_config)

    assert result == []


@pytest.mark.asyncio
async def test_nordpool_failure_without_last_good_returns_empty(monkeypatch, price_config):
    _freeze_now(monkeypatch, local_tz.localize(datetime(2026, 10, 1, 0, 0, 36)))
    with (
        patch.object(prices_mod.Prices, "fetch", side_effect=RuntimeError("502 Bad Gateway")),
        patch("ml.price_forecast.get_d1_price_forecast_fallback", new=AsyncMock(return_value=[])),
    ):
        result = await get_nordpool_data(price_config)

    assert result == []
