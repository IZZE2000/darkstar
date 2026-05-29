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
