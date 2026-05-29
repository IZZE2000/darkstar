"""Unit tests for _normalize_energy_to_kwh and sanity bound in get_load_profile_from_ha."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytz

from backend.core.ha_client import (
    _normalize_energy_to_kwh,
    get_dummy_load_profile,
    get_load_profile_from_ha,
)


class TestNormalizeEnergyToKwh:
    """Tests for _normalize_energy_to_kwh."""

    def test_standard_wh(self):
        assert _normalize_energy_to_kwh(500000, "Wh") == 500.0

    def test_uppercase_wh(self):
        assert _normalize_energy_to_kwh(500000, "WH") == 500.0

    def test_lowercase_wh(self):
        assert _normalize_energy_to_kwh(500000, "wh") == 500.0

    def test_standard_kwh(self):
        assert _normalize_energy_to_kwh(500.0, "kWh") == 500.0

    def test_uppercase_kwh(self):
        assert _normalize_energy_to_kwh(500.0, "KWH") == 500.0

    def test_standard_mwh(self):
        assert _normalize_energy_to_kwh(0.5, "MWh") == 500.0

    def test_uppercase_mwh(self):
        assert _normalize_energy_to_kwh(0.5, "MWH") == 500.0

    def test_unicode_middle_dot_variant(self):
        assert _normalize_energy_to_kwh(500000, "W·h") == 500.0

    def test_space_separated_variant(self):
        assert _normalize_energy_to_kwh(500000, "W h") == 500.0

    def test_lowercase_full_word(self):
        assert _normalize_energy_to_kwh(500000, "watthour") == 500.0

    def test_hyphenated_variant(self):
        assert _normalize_energy_to_kwh(500000, "watt-hour") == 500.0

    def test_underscore_variant(self):
        assert _normalize_energy_to_kwh(500000, "WATT_HOUR") == 500.0

    def test_hyphenated_kwh_variant(self):
        assert _normalize_energy_to_kwh(500.0, "kilowatt-hours") == 500.0

    def test_no_unit_high_value_wh_inferred(self):
        assert _normalize_energy_to_kwh(5675983, None) == 5675.983

    def test_empty_unit_high_value_wh_inferred(self):
        assert _normalize_energy_to_kwh(5675983, "") == 5675.983

    def test_no_unit_low_value_kwh_assumed(self):
        assert _normalize_energy_to_kwh(500.0, None) == 500.0

    def test_no_unit_at_threshold_kwh_assumed(self):
        assert _normalize_energy_to_kwh(100000, None) == 100000

    def test_no_unit_above_threshold_wh_inferred(self):
        assert _normalize_energy_to_kwh(100001, None) == 100.001

    def test_unknown_unit_kwh_assumed(self):
        assert _normalize_energy_to_kwh(500.0, "BTU") == 500.0


class TestLoadProfileSanityBound:
    """Tests for sanity bound in get_load_profile_from_ha."""

    @pytest.mark.asyncio
    async def test_sanity_bound_returns_dummy_profile(self):
        """Daily total exceeding 500 kWh triggers dummy profile fallback."""
        from datetime import datetime, timedelta

        from backend.core.ha_client import get_load_profile_from_ha

        config = {
            "input_sensors": {"total_load_consumption": "sensor.energy"},
        }

        now = datetime.now(pytz.UTC)
        start = now - timedelta(days=7)

        states = []
        base = 0.0
        for day in range(7):
            for slot in range(96):
                t = start + timedelta(days=day, minutes=slot * 15)
                val = base + 10.0
                states.append(
                    {
                        "state": str(val),
                        "last_changed": t.isoformat(),
                        "attributes": {"unit_of_measurement": "kWh"},
                    }
                )
                base = val

        with (
            patch(
                "backend.core.ha_client.secrets.load_home_assistant_config",
                return_value={"url": "http://ha.local", "token": "tok"},
            ),
            patch("backend.core.ha_client.httpx.AsyncClient") as mock_client_cls,
        ):
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json.return_value = [states]

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await get_load_profile_from_ha(config)

        expected = get_dummy_load_profile(config)
        assert result == expected


def _make_ha_config(url: str = "http://ha.local", token: str = "tok") -> dict:
    return {"url": url, "token": token}


def _mock_async_client(response_data):
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = response_data

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


class TestUnitPropagation:
    """Tests for unit propagation from first HA history state."""

    @pytest.mark.asyncio
    async def test_unit_propagated_from_first_state(self):
        """First state has unit Wh, subsequent states have no attributes."""
        config = {"input_sensors": {"total_load_consumption": "sensor.energy"}}
        now = datetime.now(pytz.UTC)
        start = now - timedelta(days=7)

        base_wh = 5675983.0
        states = []
        for i in range(7):
            t = start + timedelta(hours=i)
            val = base_wh + i * 10
            attrs = {"unit_of_measurement": "Wh"} if i == 0 else {}
            states.append(
                {
                    "state": str(val),
                    "last_changed": t.isoformat(),
                    "attributes": attrs,
                }
            )

        with (
            patch(
                "backend.core.ha_client.secrets.load_home_assistant_config",
                return_value=_make_ha_config(),
            ),
            patch("backend.core.ha_client.httpx.AsyncClient") as mock_client_cls,
        ):
            mock_client_cls.return_value = _mock_async_client([states])
            result = await get_load_profile_from_ha(config)

        total_daily = sum(result)
        assert total_daily < 500, f"Expected reasonable total, got {total_daily}"

    @pytest.mark.asyncio
    async def test_no_unit_magnitude_heuristic_fallback(self):
        """No state has unit_of_measurement; magnitude heuristic fires."""
        config = {"input_sensors": {"total_load_consumption": "sensor.energy"}}
        now = datetime.now(pytz.UTC)
        start = now - timedelta(days=7)

        states = []
        for i in range(7):
            t = start + timedelta(hours=i)
            val = 200000.0 + i * 100
            states.append(
                {
                    "state": str(val),
                    "last_changed": t.isoformat(),
                    "attributes": {},
                }
            )

        with (
            patch(
                "backend.core.ha_client.secrets.load_home_assistant_config",
                return_value=_make_ha_config(),
            ),
            patch("backend.core.ha_client.httpx.AsyncClient") as mock_client_cls,
        ):
            mock_client_cls.return_value = _mock_async_client([states])
            result = await get_load_profile_from_ha(config)

        total_daily = sum(result)
        assert total_daily < 500, f"Expected reasonable total, got {total_daily}"

    @pytest.mark.asyncio
    async def test_unit_change_mid_history(self):
        """First states Wh, later states switch to kWh — no crash, reasonable result."""
        config = {"input_sensors": {"total_load_consumption": "sensor.energy"}}
        now = datetime.now(pytz.UTC)
        start = now - timedelta(days=7)

        states = []
        for i in range(10):
            t = start + timedelta(hours=i)
            if i < 5:
                attrs = {"unit_of_measurement": "Wh"}
                val = 500000.0 + i * 100
            else:
                attrs = {"unit_of_measurement": "kWh"}
                val = 500.0 + i * 10
            states.append(
                {
                    "state": str(val),
                    "last_changed": t.isoformat(),
                    "attributes": attrs,
                }
            )

        with (
            patch(
                "backend.core.ha_client.secrets.load_home_assistant_config",
                return_value=_make_ha_config(),
            ),
            patch("backend.core.ha_client.httpx.AsyncClient") as mock_client_cls,
        ):
            mock_client_cls.return_value = _mock_async_client([states])
            result = await get_load_profile_from_ha(config)

        total_daily = sum(result)
        assert total_daily < 5000, f"Expected reasonable total, got {total_daily}"
        assert len(result) == 96
